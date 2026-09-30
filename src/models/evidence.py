"""Additive evidence contracts. Validation establishes structure, never truth.

These records do not extract facts, resolve conflicts, evaluate rules, or change
the existing answer API. Native Pydantic JSON methods are the wire interface.
"""
from __future__ import annotations

from decimal import Decimal
from ipaddress import ip_address
from urllib.parse import urlsplit
from typing import Annotated, Literal

from pydantic import (
    AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field,
    StrictBool, StrictFloat, StrictInt, StrictStr, field_validator, model_validator,
)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    return value  # Preserve exact source text, including surrounding whitespace.


Text = Annotated[StrictStr, AfterValidator(_nonblank)]
Version = Annotated[StrictInt, Field(gt=0)]
Scalar = StrictBool | StrictInt | StrictFloat | StrictStr
DocumentClass = Literal[
    "marketing", "faq", "provider_standard_terms", "regulator_model",
    "transaction_specific_disclosure", "user_supplied_schedule",
    "donated_agreement", "synthetic_counterfactual", "provider_claim",
]
UnobservedReason = Literal[
    "not_publicly_found", "login_gated", "access_blocked", "in_customer_schedule",
]
AccessStatus = Literal["accessible", "not_publicly_found", "login_gated", "access_blocked", "in_customer_schedule"]
Intent = Literal["named_offer", "described_operation", "definition", "out_of_scope"]
NON_HUMAN_REVIEWERS = frozenset({"auto", "automatic", "model", "llm", "model-confidence", "claude", "gpt", "system", "bot"})


def require_human_reviewer(value: str) -> str:
    """Approval identities must name a person; automatic identities never approve."""
    if value.strip().lower() in NON_HUMAN_REVIEWERS:
        raise ValueError("automatic identity cannot review or approve")
    return value


def _public_http_url(value):
    if value is None:
        return value
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("provenance URLs must not carry credentials, query strings or fragments")
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("provenance URLs must be public")
    try:
        address = ip_address(host)
    except ValueError:
        return value
    if not address.is_global:
        raise ValueError("provenance URLs must be public")
    return value


FACT_SLOTS = (
    "asset", "seller", "sales_channel", "financing_party", "contract_family",
    "cash_price", "financed_or_final_price", "down_payment", "instalment_count",
    "instalment_amount", "additional_fees", "late_payment_clause",
    "late_fee_beneficiary", "insurance_leg", "ownership_risk_sequence",
    "early_settlement", "refund_terms",
)


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always", allow_inf_nan=False)

    def model_copy(self, *, update=None, deep=False):
        """Unlike BaseModel.model_copy, updates must pass full validation."""
        return type(self).model_validate({**self.model_dump(), **(update or {})})


class EvidenceScope(EvidenceModel):
    lane: Literal["company", "personal", "general"]
    entity_id: Text | None = None
    product_id: Text | None = None
    seller_id: Text | None = None
    financier_id: Text | None = None
    channel_id: Text | None = None
    transaction_id: Text | None = None
    document_scope: Literal["template", "schedule", "offer", "general"]

    @model_validator(mode="after")
    def identity(self):
        if self.lane == "company" and not self.entity_id:
            raise ValueError("company scope requires entity_id")
        if self.lane == "personal" and not self.transaction_id:
            raise ValueError("personal scope requires transaction_id")
        if self.lane != "personal" and self.transaction_id:
            raise ValueError("transaction identity belongs to personal scope")
        return self


class CaptureManifest(EvidenceModel):
    source_id: Text
    url: Annotated[StrictStr, Field(pattern=r"^https?://[^\s/]+(?:/[^\s]*)?$")]
    final_url: Annotated[StrictStr, Field(pattern=r"^https?://[^\s/]+(?:/[^\s]*)?$")] | None = None
    captured_at: AwareDatetime
    sha256: Annotated[StrictStr, Field(pattern=r"^[0-9a-fA-F]{64}$")]
    content_type: Text
    language: Text
    access_status: AccessStatus
    document_version: Text

    @field_validator("url", "final_url")
    @classmethod
    def public_url(cls, value):
        return _public_http_url(value)

    @field_validator("sha256")
    @classmethod
    def lowercase_digest(cls, value):
        return value.lower()


class SourceProvenance(EvidenceModel):
    kind: Literal["source"] = "source"
    capture: CaptureManifest
    document_class: DocumentClass
    exact_text: Text
    span_id: Text
    scope: EvidenceScope


class UserTurnProvenance(EvidenceModel):
    kind: Literal["user_turn"] = "user_turn"
    session_id: Text
    turn_id: Text
    exact_text: Text
    recorded_at: AwareDatetime
    version: Version
    scope: EvidenceScope

    @model_validator(mode="after")
    def personal_only(self):
        if self.scope.lane != "personal":
            raise ValueError("user turns can establish personal facts only")
        return self


Provenance = Annotated[SourceProvenance | UserTurnProvenance, Field(discriminator="kind")]


class Money(EvidenceModel):
    amount: Annotated[StrictInt | Decimal, Field(ge=0)]
    currency: Annotated[StrictStr, Field(pattern=r"^[A-Z]{3}$")]

    @field_validator("amount", mode="before")
    @classmethod
    def exact_decimal(cls, value):
        if type(value) not in (int, Decimal, str):
            raise ValueError("money requires an integer, Decimal, or exact decimal string")
        if type(value) is not int:
            try:
                digits = len(Decimal(value).as_tuple().digits)
            except ArithmeticError:
                return value  # Let field validation report the malformed amount.
            if digits > 40:
                raise ValueError("money amount has too many digits")
        return value


FactValue = Scalar | Money | tuple[Scalar, ...]


class FactCandidate(EvidenceModel):
    value: FactValue
    status: Literal["observed", "user_reported"]
    source: Provenance

    @model_validator(mode="after")
    def authority(self):
        if self.status == "user_reported" and not isinstance(self.source, UserTurnProvenance):
            raise ValueError("user_reported requires user-turn provenance")
        if self.status == "observed":
            if not isinstance(self.source, SourceProvenance):
                raise ValueError("observed requires source provenance")
            if self.source.document_class == "synthetic_counterfactual":
                raise ValueError("synthetic material is never observed evidence")
            if self.source.capture.access_status != "accessible":
                raise ValueError("observed span requires an accessible capture")
        return self


def _canonical_value(value):
    """Numerically equal money is one value however its amount was spelled."""
    if isinstance(value, Money):
        return ("Money", Decimal(value.amount).normalize(), value.currency)
    return (type(value).__name__, repr(value))


class FactObservation(EvidenceModel):
    slot: Text  # Named companion slots and extensible rule-specific slots.
    scope: EvidenceScope
    version: Version
    recorded_at: AwareDatetime
    status: Literal["observed", "user_reported", "conflicting", "unknown"]
    value: FactValue | None = None
    source: Provenance | None = None
    unobserved_reason: UnobservedReason | None = None
    candidates: tuple[FactCandidate, ...] = ()
    access_attempts: tuple[CaptureManifest, ...] = ()

    @model_validator(mode="after")
    def consistent_evidence(self):
        supported = []
        if self.status == "unknown":
            if self.value is not None or self.source is not None or self.candidates or not self.unobserved_reason:
                raise ValueError("unknown requires a reason and no asserted value or supporting span")
        elif self.status == "conflicting":
            if self.value is not None or self.source is not None or self.unobserved_reason or len(self.candidates) < 2:
                raise ValueError("conflict requires at least two supported candidates and no selected value")
            if len({_canonical_value(c.value) for c in self.candidates}) < 2:
                raise ValueError("conflict requires distinct values")
            supported = list(self.candidates)
        else:
            if self.value is None or self.source is None or self.candidates or self.unobserved_reason:
                raise ValueError("known fact requires value and source only")
            supported = [FactCandidate(value=self.value, status=self.status, source=self.source)]
        for candidate in supported:
            if candidate.source.scope != self.scope:
                raise ValueError("fact and provenance scopes must match")
            if (self.slot == "contract_family" and isinstance(candidate.source, SourceProvenance)
                    and candidate.source.document_class == "provider_claim"):
                raise ValueError("provider self-label cannot establish contract mechanism")
            if self.slot == "instalment_count" and (type(candidate.value) is not int or candidate.value < 0):
                raise ValueError("instalment_count requires a nonnegative integer")
            if self.slot in {"cash_price", "financed_or_final_price", "down_payment", "instalment_amount"} and not isinstance(candidate.value, Money):
                raise ValueError("monetary slots require an amount and currency")
        return self


class FactSnapshot(EvidenceModel):
    snapshot_id: Text
    version: Version
    recorded_at: AwareDatetime
    facts: tuple[FactObservation, ...] = ()

    @model_validator(mode="after")
    def unique_active_facts(self):
        identities = [(fact.slot, fact.scope.model_dump_json()) for fact in self.facts]
        if len(identities) != len(set(identities)):
            raise ValueError("snapshot requires one active fact per slot and scope; use conflicting candidates")
        return self


class FactResolution(EvidenceModel):
    """A user confirms their own conflicting assertions; not document verification."""
    previous_fact: FactObservation
    selected_fact: FactObservation
    basis: Literal["user_confirmed_schedule"] = "user_confirmed_schedule"

    @model_validator(mode="after")
    def own_assertions_only(self):
        old, selected = self.previous_fact, self.selected_fact
        if old.status != "conflicting" or selected.status != "user_reported":
            raise ValueError("resolution requires a conflict and a new user assertion")
        if old.slot != selected.slot or old.scope != selected.scope:
            raise ValueError("resolution must retain the fact slot and transaction scope")
        if selected.version <= old.version or selected.recorded_at < old.recorded_at:
            raise ValueError("resolution must be newer than the conflicting fact")
        if not isinstance(selected.source, UserTurnProvenance):
            raise ValueError("user resolution requires turn provenance")
        if (selected.source.version != selected.version or selected.source.recorded_at > selected.recorded_at
                or selected.source.recorded_at < old.recorded_at):
            raise ValueError("resolution provenance must identify the new chronological assertion")
        if any(not isinstance(candidate.source, UserTurnProvenance)
               or candidate.source.session_id != selected.source.session_id for candidate in old.candidates):
            raise ValueError("a user can resolve only their own assertions, not observed source conflicts")
        return self


class DossierRole(EvidenceModel):
    role: Text
    party_id: Text
    evidence: tuple[SourceProvenance, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def observed_role(self):
        for source in self.evidence:
            FactCandidate(value=self.party_id, status="observed", source=source)
            if source.document_class == "provider_claim":
                raise ValueError("a Sharia self-label cannot establish a party role")
        return self


class LinkEdge(EvidenceModel):
    from_url: Text
    to_url: Text
    relation: Text


class BuyerJourneyStep(EvidenceModel):
    order: Annotated[StrictInt, Field(ge=1)]
    url: Text
    description: Text
    access_status: AccessStatus


class VerificationRecord(EvidenceModel):
    reviewer_id: Annotated[Text, AfterValidator(require_human_reviewer)]
    recorded_at: AwareDatetime
    decision: Literal["pending", "verified", "rejected", "approved"]
    notes: Text


class Dossier(EvidenceModel):
    dossier_id: Text
    entity_name: Text
    aliases: tuple[Text, ...] = ()
    official_domain: Text
    scope: EvidenceScope
    document_version: Text
    operation_id: Text
    published_offer_period: Text | None = None
    roles: tuple[DossierRole, ...] = ()
    link_graph: tuple[LinkEdge, ...] = ()
    public_buyer_journey: tuple[BuyerJourneyStep, ...] = ()
    capture_manifest: tuple[CaptureManifest, ...] = ()
    field_observations: tuple[FactObservation, ...] = ()
    older_versions: tuple[Text, ...] = ()
    conflicts: tuple[Text, ...] = ()
    analyst_verification: VerificationRecord | None = None
    scholar_rule_mapping_review: VerificationRecord | None = None

    @model_validator(mode="after")
    def company_boundary(self):
        if self.scope.lane != "company":
            raise ValueError("dossiers describe company evidence")
        if any(f.scope != self.scope for f in self.field_observations):
            raise ValueError("dossier observations must match dossier scope")
        if any(e.scope != self.scope for role in self.roles for e in role.evidence):
            raise ValueError("dossier role evidence must match dossier scope")
        captures = list(self.capture_manifest)
        captures.extend(e.capture for role in self.roles for e in role.evidence)
        for observation in self.field_observations:
            sources = ([observation.source] if observation.source else []) + [c.source for c in observation.candidates]
            captures.extend(s.capture for s in sources if isinstance(s, SourceProvenance))
            captures.extend(observation.access_attempts)
        identities = {}
        for capture in captures:
            key = (capture.source_id, capture.captured_at, capture.document_version)
            if key in identities and identities[key] != capture:
                raise ValueError("one capture identity cannot have conflicting manifests")
            identities[key] = capture
        allowed_versions = {self.document_version, *self.older_versions}
        if any(c.document_version not in allowed_versions for c in captures):
            raise ValueError("evidence version must be current or explicitly retained as an older version")
        orders = [s.order for s in self.public_buyer_journey]
        if orders != sorted(set(orders)):
            raise ValueError("buyer journey steps must have unique ascending order")
        return self


class GateDecision(EvidenceModel):
    gate: Literal["intent_and_scope", "typed_extraction", "contract_family", "material_fact",
                  "source_and_version", "claim_support", "selective_answer", "review_and_feedback"]
    status: Literal["passed", "blocked", "not_applicable"]
    reason: Text
    evidence_ids: tuple[Text, ...] = ()


class RuleReference(EvidenceModel):
    rule_id: Text
    version: Version


class CitedClaim(EvidenceModel):
    text: Text
    sources: tuple[Provenance, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def admissible_sources(self):
        for source in self.sources:
            FactCandidate(value=self.text, status="observed" if isinstance(source, SourceProvenance) else "user_reported", source=source)
        return self


class AnswerDecision(EvidenceModel):
    decision: Literal["ANSWER", "CLARIFICATION_NEEDED", "INSUFFICIENT_DATA"]
    reason: Text
    questions: tuple[Text, ...] = ()
    needed_documents_or_reviews: tuple[Text, ...] = ()
    answer: Text | None = None
    cited_claims: tuple[CitedClaim, ...] = ()
    rule_references: tuple[RuleReference, ...] = ()
    gates: tuple[GateDecision, ...] = ()

    @model_validator(mode="after")
    def decision_shape(self):
        if len({gate.gate for gate in self.gates}) != len(self.gates):
            raise ValueError("decision must contain at most one result for each gate")
        if self.decision == "CLARIFICATION_NEEDED":
            if len(self.questions) != 1 or self.answer is not None or self.cited_claims or self.rule_references:
                raise ValueError("clarification requires exactly one question and no answer")
            question = self.questions[0].strip()
            if ("\n" in question or "\r" in question or question.count("?") + question.count("؟") != 1
                    or question.startswith(("-", "*", "1.", "2."))):
                raise ValueError("clarification requires exactly one concise question")
        elif self.questions:
            raise ValueError("questions belong only to clarification decisions")
        if self.decision == "INSUFFICIENT_DATA":
            if not self.needed_documents_or_reviews or self.answer is not None or self.cited_claims or self.rule_references:
                raise ValueError("insufficiency must name needed documents or review and withhold answer")
        if self.decision == "ANSWER" and (self.answer is None or not self.cited_claims):
            raise ValueError("answer requires text and attributed claims")
        return self


class DecisionReviewRow(EvidenceModel):
    review_id: Text
    request_id: Text
    session_id: Text
    turn_id: Text
    version: Version
    recorded_at: AwareDatetime
    intent: Intent
    query: Text
    fact_snapshot: FactSnapshot
    decision: AnswerDecision
    clarifying_turn: UserTurnProvenance | None = None
    fact_resolutions: tuple[FactResolution, ...] = ()

    @model_validator(mode="after")
    def same_session(self):
        sources = [self.clarifying_turn] if self.clarifying_turn else []
        for fact in self.fact_snapshot.facts:
            if fact.source:
                sources.append(fact.source)
            sources.extend(candidate.source for candidate in fact.candidates)
        sources.extend(source for claim in self.decision.cited_claims for source in claim.sources)
        for resolution in self.fact_resolutions:
            if (resolution.selected_fact not in self.fact_snapshot.facts
                    or resolution.selected_fact.version != self.version
                    or resolution.selected_fact.source.turn_id != self.turn_id):
                raise ValueError("resolution must select the current review turn's active fact")
            sources.append(resolution.selected_fact.source)
            sources.extend(candidate.source for candidate in resolution.previous_fact.candidates)
        if any(isinstance(source, UserTurnProvenance) and source.session_id != self.session_id for source in sources):
            raise ValueError("all user-turn provenance must belong to review session")
        return self
