"""Canonical institution registry records for the Egypt evidence corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional


class InstitutionRegulator(str, Enum):
    CBE = "cbe"
    FRA = "fra"
    EGX = "egx"
    MCSD = "mcsd"
    UNKNOWN = "unknown"


class InstitutionSector(str, Enum):
    BANK = "bank"
    PAYMENT_SERVICE = "payment_service"
    CAPITAL_MARKET = "capital_market"
    INSURANCE = "insurance"
    TAKAFUL = "takaful"
    MORTGAGE_FINANCE = "mortgage_finance"
    LEASING = "leasing"
    CONSUMER_FINANCE = "consumer_finance"
    MICROFINANCE = "microfinance"
    SME_FINANCE = "sme_finance"
    FINTECH = "fintech"
    FUND = "fund"
    SUKUK = "sukuk"
    NON_BANK_FINANCE = "non_bank_finance"
    UNKNOWN = "unknown"


class InstitutionRefreshStatus(str, Enum):
    BASELINE_UNVERIFIED = "baseline_unverified"
    REGULATOR_REVALIDATED = "regulator_revalidated"
    STALE = "stale"
    REJECTED = "rejected"


class InstitutionDiscoveryStatus(str, Enum):
    NOT_STARTED = "not_started"
    OFFICIAL_SITE_CONFIRMED = "official_site_confirmed"
    OFFICIAL_SITE_NOT_FOUND = "official_site_not_found"
    SITE_UNREACHABLE = "site_unreachable"
    BLOCKED_BY_SECURITY = "blocked_by_security"
    REQUIRES_LOGIN = "requires_login"
    DOCUMENT_NOT_PUBLIC = "document_not_public"
    INSUFFICIENT_PUBLIC_DATA = "insufficient_public_data"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class DiscoveryEvidenceType(str, Enum):
    REGULATOR_LINK = "regulator_link"
    OFFICIAL_WEBSITE = "official_website"
    SEARCH_RESULT = "search_result"
    MANUAL_REVIEW = "manual_review"


class DiscoveryStopReason(str, Enum):
    CONFIRMED_OFFICIAL_SITE = "confirmed_official_site"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"
    BLOCKED_BY_SECURITY = "blocked_by_security"
    REQUIRES_LOGIN = "requires_login"
    DOCUMENT_NOT_PUBLIC = "document_not_public"
    SITE_UNREACHABLE = "site_unreachable"
    INSUFFICIENT_PUBLIC_DATA = "insufficient_public_data"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class PublicArtifactType(str, Enum):
    TARIFF = "tariff"
    TERMS = "terms"
    CONTRACT = "contract"
    MODEL_CONTRACT = "model_contract"
    ANNUAL_REPORT = "annual_report"
    PROSPECTUS = "prospectus"
    SUKUK_DOCUMENT = "sukuk_document"
    FUND_DOCUMENT = "fund_document"
    POLICY_WORDING = "policy_wording"
    REGULATOR_RULEBOOK = "regulator_rulebook"
    PRODUCT_PAGE = "product_page"
    OTHER = "other"


class OperationEvidenceField(str, Enum):
    FEES = "fees"
    PAYMENT_TERMS = "payment_terms"
    LATE_PAYMENT_CLAUSES = "late_payment_clauses"
    PENALTY_BENEFICIARY = "penalty_beneficiary"
    COLLATERAL = "collateral"
    GUARANTEES = "guarantees"
    INSURANCE_TAKAFUL_LINKS = "insurance_takaful_links"
    OWNERSHIP_OR_ASSET_FLOW = "ownership_or_asset_flow"
    SHARIA_CLAIMS = "sharia_claims"


class ReviewCandidateStatus(str, Enum):
    MACHINE_PROPOSED = "machine_proposed"
    SCHOLAR_ACCEPTED = "scholar_accepted"
    SCHOLAR_REJECTED = "scholar_rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class ComplianceRiskLabel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class PublicArtifactAuthorityRank(str, Enum):
    REGULATOR = "regulator"
    OFFICIAL_INSTITUTION = "official_institution"
    EXCHANGE_OR_DEPOSITORY = "exchange_or_depository"
    PROSPECTUS_OR_OFFERING_DOCUMENT = "prospectus_or_offering_document"
    THIRD_PARTY_DISCOVERY_ONLY = "third_party_discovery_only"


class ExtractionStatus(str, Enum):
    NOT_STARTED = "not_started"
    EXTRACTED = "extracted"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_PUBLIC = "not_public"
    REQUIRES_LOGIN = "requires_login"
    BLOCKED_BY_SECURITY = "blocked_by_security"


class AccessControlSignal(str, Enum):
    ROBOTS_DISALLOW = "robots_disallow"
    TERMS_DISALLOW = "terms_disallow"
    RATE_LIMITED = "rate_limited"
    CAPTCHA = "captcha"
    LOGIN_REQUIRED = "login_required"
    PAYWALL = "paywall"
    SECURITY_BLOCK = "security_block"


class AccessDecisionStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"
    BLOCKED_BY_TERMS = "blocked_by_terms"
    RATE_LIMITED = "rate_limited"
    BLOCKED_BY_SECURITY = "blocked_by_security"
    REQUIRES_LOGIN = "requires_login"
    DOCUMENT_NOT_PUBLIC = "document_not_public"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


def stable_institution_id(name: str, regulator: InstitutionRegulator, sector: InstitutionSector) -> str:
    """Return a stable, human-readable ID for baseline registry seeds."""
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    if not normalized:
        raise ValueError("institution name must produce a stable id")
    return f"{regulator.value}-{sector.value}-{normalized}"


@dataclass(frozen=True)
class AccessControlDecision:
    """Ethical access-control gate before any artifact fetch is attempted."""

    url: str
    status: AccessDecisionStatus
    checked_at: date
    signals: List[AccessControlSignal] = field(default_factory=list)
    retry_after_seconds: Optional[int] = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.url.startswith(("https://", "http://")):
            raise ValueError("url must be an HTTP(S) URL")
        if self.retry_after_seconds is not None and self.retry_after_seconds < 0:
            raise ValueError("retry_after_seconds cannot be negative")
        if self.status != AccessDecisionStatus.ALLOWED and not self.reason.strip():
            raise ValueError("reason is required when access is not allowed")
        if self.status == AccessDecisionStatus.ALLOWED and self.signals:
            raise ValueError("allowed access cannot include blocking signals")

    @classmethod
    def evaluate(
        cls,
        *,
        url: str,
        checked_at: date,
        signals: Iterable[AccessControlSignal] = (),
        retry_after_seconds: Optional[int] = None,
        reason: str = "",
    ) -> "AccessControlDecision":
        signal_set = list(signals)
        status = _access_status_for_signals(signal_set)
        if status == AccessDecisionStatus.RATE_LIMITED and retry_after_seconds is None:
            reason = reason or "Rate limit encountered; pause instead of retrying aggressively."
        return cls(
            url=url,
            status=status,
            checked_at=checked_at,
            signals=signal_set,
            retry_after_seconds=retry_after_seconds,
            reason=reason,
        )

    @property
    def allows_fetch(self) -> bool:
        return self.status == AccessDecisionStatus.ALLOWED

    def to_discovery_status(self) -> InstitutionDiscoveryStatus:
        mapping = {
            AccessDecisionStatus.ALLOWED: InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
            AccessDecisionStatus.BLOCKED_BY_ROBOTS: InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.BLOCKED_BY_TERMS: InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.RATE_LIMITED: InstitutionDiscoveryStatus.SITE_UNREACHABLE,
            AccessDecisionStatus.BLOCKED_BY_SECURITY: InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.REQUIRES_LOGIN: InstitutionDiscoveryStatus.REQUIRES_LOGIN,
            AccessDecisionStatus.DOCUMENT_NOT_PUBLIC: InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC,
            AccessDecisionStatus.MANUAL_REVIEW_REQUIRED: InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
        }
        return mapping[self.status]

    def to_extraction_status(self) -> ExtractionStatus:
        mapping = {
            AccessDecisionStatus.ALLOWED: ExtractionStatus.NOT_STARTED,
            AccessDecisionStatus.BLOCKED_BY_ROBOTS: ExtractionStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.BLOCKED_BY_TERMS: ExtractionStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.RATE_LIMITED: ExtractionStatus.FAILED,
            AccessDecisionStatus.BLOCKED_BY_SECURITY: ExtractionStatus.BLOCKED_BY_SECURITY,
            AccessDecisionStatus.REQUIRES_LOGIN: ExtractionStatus.REQUIRES_LOGIN,
            AccessDecisionStatus.DOCUMENT_NOT_PUBLIC: ExtractionStatus.NOT_PUBLIC,
            AccessDecisionStatus.MANUAL_REVIEW_REQUIRED: ExtractionStatus.FAILED,
        }
        return mapping[self.status]

    def to_dict(self) -> Dict[str, object]:
        return {
            "url": self.url,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "signals": [signal.value for signal in self.signals],
            "retry_after_seconds": self.retry_after_seconds,
            "reason": self.reason,
            "allows_fetch": self.allows_fetch,
        }


def _access_status_for_signals(signals: List[AccessControlSignal]) -> AccessDecisionStatus:
    priority = (
        (AccessControlSignal.ROBOTS_DISALLOW, AccessDecisionStatus.BLOCKED_BY_ROBOTS),
        (AccessControlSignal.TERMS_DISALLOW, AccessDecisionStatus.BLOCKED_BY_TERMS),
        (AccessControlSignal.CAPTCHA, AccessDecisionStatus.BLOCKED_BY_SECURITY),
        (AccessControlSignal.SECURITY_BLOCK, AccessDecisionStatus.BLOCKED_BY_SECURITY),
        (AccessControlSignal.LOGIN_REQUIRED, AccessDecisionStatus.REQUIRES_LOGIN),
        (AccessControlSignal.PAYWALL, AccessDecisionStatus.DOCUMENT_NOT_PUBLIC),
        (AccessControlSignal.RATE_LIMITED, AccessDecisionStatus.RATE_LIMITED),
    )
    for signal, status in priority:
        if signal in signals:
            return status
    return AccessDecisionStatus.ALLOWED


@dataclass(frozen=True)
class OfficialSiteDiscoveryAttempt:
    """One bounded discovery attempt for an institution official site."""

    attempt_number: int
    evidence_type: DiscoveryEvidenceType
    evidence_url: str
    confidence: float
    status: InstitutionDiscoveryStatus
    checked_at: date
    stop_reason: Optional[DiscoveryStopReason] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")
        if not self.evidence_url.startswith(("https://", "http://")):
            raise ValueError("evidence_url must be an HTTP(S) URL")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == InstitutionDiscoveryStatus.NOT_STARTED:
            raise ValueError("attempt status cannot be not_started")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "OfficialSiteDiscoveryAttempt":
        data = dict(payload)
        data["evidence_type"] = DiscoveryEvidenceType(data["evidence_type"])
        data["status"] = InstitutionDiscoveryStatus(data["status"])
        if data.get("stop_reason"):
            data["stop_reason"] = DiscoveryStopReason(data["stop_reason"])
        if isinstance(data.get("checked_at"), str):
            data["checked_at"] = date.fromisoformat(str(data["checked_at"]))
        return cls(**data)

    def to_dict(self) -> Dict[str, object]:
        return {
            "attempt_number": self.attempt_number,
            "evidence_type": self.evidence_type.value,
            "evidence_url": self.evidence_url,
            "confidence": self.confidence,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class OfficialSiteDiscoveryResult:
    """Final bounded discovery result derived from ordered attempts."""

    institution_id: str
    attempts: List[OfficialSiteDiscoveryAttempt]
    status: InstitutionDiscoveryStatus
    stop_reason: DiscoveryStopReason
    selected_url: Optional[str] = None
    confidence: float = 0.0
    gap_reason: str = ""

    def __post_init__(self) -> None:
        if not self.institution_id.strip():
            raise ValueError("institution_id is required")
        if not self.attempts:
            raise ValueError("at least one discovery attempt is required")
        expected_numbers = list(range(1, len(self.attempts) + 1))
        actual_numbers = [attempt.attempt_number for attempt in self.attempts]
        if actual_numbers != expected_numbers:
            raise ValueError("attempts must be ordered and contiguous")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED:
            if not self.selected_url:
                raise ValueError("selected_url is required when official site is confirmed")
        elif not self.gap_reason.strip():
            raise ValueError("gap_reason is required when official site is not confirmed")

    @classmethod
    def from_attempts(
        cls,
        institution_id: str,
        attempts: Iterable[OfficialSiteDiscoveryAttempt],
    ) -> "OfficialSiteDiscoveryResult":
        ordered = sorted(attempts, key=lambda attempt: attempt.attempt_number)
        if not ordered:
            raise ValueError("at least one discovery attempt is required")
        best = max(ordered, key=lambda attempt: attempt.confidence)
        final = ordered[-1]
        status = final.status
        stop_reason = final.stop_reason or _default_stop_reason(status)
        if status == InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED:
            return cls(
                institution_id=institution_id,
                attempts=ordered,
                status=status,
                stop_reason=stop_reason,
                selected_url=best.evidence_url,
                confidence=best.confidence,
            )
        return cls(
            institution_id=institution_id,
            attempts=ordered,
            status=status,
            stop_reason=stop_reason,
            confidence=best.confidence,
            gap_reason=final.notes or stop_reason.value,
        )

    def to_registry_updates(self) -> Dict[str, object]:
        return {
            "discovery_status": self.status,
            "official_website": self.selected_url,
            "official_website_confidence": self.confidence,
            "attempt_count": len(self.attempts),
            "last_checked_at": self.attempts[-1].checked_at,
            "gap_reason": self.gap_reason,
        }


@dataclass(frozen=True)
class PublicArtifactRecord:
    """Captured public artifact metadata for future institution evidence."""

    artifact_id: str
    institution_id: str
    url: str
    authority_rank: PublicArtifactAuthorityRank
    artifact_type: PublicArtifactType
    language: str
    retrieved_at: date
    http_status: int
    content_type: str
    content_hash: str
    extraction_status: ExtractionStatus
    citation_anchor_strategy: str
    raw_path: Optional[str] = None
    text_path: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact_id is required")
        if not self.institution_id.strip():
            raise ValueError("institution_id is required")
        if not self.url.startswith(("https://", "http://")):
            raise ValueError("url must be an HTTP(S) URL")
        if self.language not in {"en", "ar", "mixed", "unknown"}:
            raise ValueError("language must be en, ar, mixed, or unknown")
        if not 100 <= self.http_status <= 599:
            raise ValueError("http_status must be a valid HTTP status code")
        if not self.content_type.strip():
            raise ValueError("content_type is required")
        if not self.content_hash.startswith("sha256:"):
            raise ValueError("content_hash must start with sha256:")
        if not self.citation_anchor_strategy.strip():
            raise ValueError("citation_anchor_strategy is required")
        if self.extraction_status in {ExtractionStatus.EXTRACTED, ExtractionStatus.PARTIAL}:
            if not self.raw_path or not self.text_path:
                raise ValueError("raw_path and text_path are required for extracted artifacts")
        if self.authority_rank == PublicArtifactAuthorityRank.THIRD_PARTY_DISCOVERY_ONLY:
            if self.extraction_status == ExtractionStatus.EXTRACTED:
                raise ValueError("third-party discovery artifacts cannot be extracted as compliance evidence")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "PublicArtifactRecord":
        data = dict(payload)
        data["authority_rank"] = PublicArtifactAuthorityRank(data["authority_rank"])
        data["artifact_type"] = PublicArtifactType(data["artifact_type"])
        data["extraction_status"] = ExtractionStatus(data["extraction_status"])
        if isinstance(data.get("retrieved_at"), str):
            data["retrieved_at"] = date.fromisoformat(str(data["retrieved_at"]))
        return cls(**data)

    def to_dict(self) -> Dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "institution_id": self.institution_id,
            "url": self.url,
            "authority_rank": self.authority_rank.value,
            "artifact_type": self.artifact_type.value,
            "language": self.language,
            "retrieved_at": self.retrieved_at.isoformat(),
            "http_status": self.http_status,
            "content_type": self.content_type,
            "content_hash": self.content_hash,
            "raw_path": self.raw_path,
            "text_path": self.text_path,
            "extraction_status": self.extraction_status.value,
            "citation_anchor_strategy": self.citation_anchor_strategy,
            "notes": self.notes,
        }

    @property
    def priority_score(self) -> int:
        artifact_priority = {
            PublicArtifactType.TARIFF: 100,
            PublicArtifactType.TERMS: 95,
            PublicArtifactType.CONTRACT: 100,
            PublicArtifactType.MODEL_CONTRACT: 100,
            PublicArtifactType.ANNUAL_REPORT: 80,
            PublicArtifactType.PROSPECTUS: 95,
            PublicArtifactType.SUKUK_DOCUMENT: 95,
            PublicArtifactType.FUND_DOCUMENT: 90,
            PublicArtifactType.POLICY_WORDING: 90,
            PublicArtifactType.REGULATOR_RULEBOOK: 100,
            PublicArtifactType.PRODUCT_PAGE: 60,
            PublicArtifactType.OTHER: 10,
        }
        authority_bonus = {
            PublicArtifactAuthorityRank.REGULATOR: 30,
            PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION: 25,
            PublicArtifactAuthorityRank.EXCHANGE_OR_DEPOSITORY: 20,
            PublicArtifactAuthorityRank.PROSPECTUS_OR_OFFERING_DOCUMENT: 25,
            PublicArtifactAuthorityRank.THIRD_PARTY_DISCOVERY_ONLY: -100,
        }
        return artifact_priority[self.artifact_type] + authority_bonus[self.authority_rank]


@dataclass(frozen=True)
class OperationEvidenceSpan:
    """A quoted-or-paraphrased evidence span attached to an institution operation."""

    artifact_id: str
    field: OperationEvidenceField
    text: str
    page: Optional[int] = None
    section: str = ""
    citation_anchor: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact_id is required")
        if not self.text.strip():
            raise ValueError("text is required")
        if self.page is not None and self.page < 1:
            raise ValueError("page must be positive")


@dataclass(frozen=True)
class OperationCatalogRecord:
    """Evidence-backed operation/product record for an institution."""

    operation_id: str
    institution_id: str
    operation_name: str
    artifact_ids: List[str]
    evidence_spans: List[OperationEvidenceSpan] = field(default_factory=list)
    user_supplied_override: bool = False
    stale_or_conflicting_public_data: bool = False

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("operation_id is required")
        if not self.institution_id.strip():
            raise ValueError("institution_id is required")
        if not self.operation_name.strip():
            raise ValueError("operation_name is required")
        if not self.artifact_ids:
            raise ValueError("artifact_ids is required")
        missing_artifacts = {
            span.artifact_id for span in self.evidence_spans if span.artifact_id not in self.artifact_ids
        }
        if missing_artifacts:
            raise ValueError(f"evidence span references unknown artifact_id: {sorted(missing_artifacts)[0]}")

    def fields_present(self) -> List[OperationEvidenceField]:
        return sorted({span.field for span in self.evidence_spans}, key=lambda field: field.value)


@dataclass(frozen=True)
class MachineAaoifiMappingCandidate:
    """Machine-proposed mapping; never accepted truth until scholar review."""

    mapping_id: str
    operation_id: str
    candidate_standards: List[str]
    risk_label: ComplianceRiskLabel
    rationale: str
    status: ReviewCandidateStatus = ReviewCandidateStatus.MACHINE_PROPOSED

    def __post_init__(self) -> None:
        if not self.mapping_id.strip():
            raise ValueError("mapping_id is required")
        if not self.operation_id.strip():
            raise ValueError("operation_id is required")
        if not self.candidate_standards:
            raise ValueError("candidate_standards is required")
        if not self.rationale.strip():
            raise ValueError("rationale is required")
        if self.status != ReviewCandidateStatus.MACHINE_PROPOSED:
            raise ValueError("machine mappings must start as machine_proposed")


@dataclass(frozen=True)
class ScholarReviewRecord:
    """Human review decision that can promote a machine candidate into gold data."""

    review_id: str
    mapping_id: str
    reviewer: str
    decision: ReviewCandidateStatus
    aaoifi_references: List[str]
    rationale: str
    uncertainty_flags: List[str] = field(default_factory=list)
    correction_type: str = ""
    accepted_gold_case: bool = False

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id is required")
        if not self.mapping_id.strip():
            raise ValueError("mapping_id is required")
        if not self.reviewer.strip():
            raise ValueError("reviewer is required")
        if self.decision == ReviewCandidateStatus.MACHINE_PROPOSED:
            raise ValueError("scholar review decision cannot be machine_proposed")
        if self.accepted_gold_case and self.decision != ReviewCandidateStatus.SCHOLAR_ACCEPTED:
            raise ValueError("accepted gold cases must be scholar_accepted")
        if not self.aaoifi_references:
            raise ValueError("aaoifi_references is required")
        if not self.rationale.strip():
            raise ValueError("rationale is required")


@dataclass(frozen=True)
class UserFactOverrideDecision:
    """Records when user-supplied facts supersede stale public corpus assumptions."""

    operation_id: str
    user_facts: Dict[str, str]
    public_conflict_flags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("operation_id is required")
        if not self.user_facts:
            raise ValueError("user_facts is required")

    @property
    def should_prioritize_user_facts(self) -> bool:
        return True

    @property
    def should_flag_public_data(self) -> bool:
        return bool(self.public_conflict_flags)


@dataclass(frozen=True)
class CorpusPilotPlan:
    """Small pilot gate before scaling registry ingestion."""

    pilot_id: str
    institution_ids: List[str]
    includes_no_details_case: bool

    def __post_init__(self) -> None:
        if not self.pilot_id.strip():
            raise ValueError("pilot_id is required")
        if len(set(self.institution_ids)) < 3:
            raise ValueError("pilot must include at least three mixed institutions")
        if not self.includes_no_details_case:
            raise ValueError("pilot must include one no-details-found hard case")


def _default_stop_reason(status: InstitutionDiscoveryStatus) -> DiscoveryStopReason:
    mapping = {
        InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED: DiscoveryStopReason.CONFIRMED_OFFICIAL_SITE,
        InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND: DiscoveryStopReason.MAX_ATTEMPTS_REACHED,
        InstitutionDiscoveryStatus.SITE_UNREACHABLE: DiscoveryStopReason.SITE_UNREACHABLE,
        InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY: DiscoveryStopReason.BLOCKED_BY_SECURITY,
        InstitutionDiscoveryStatus.REQUIRES_LOGIN: DiscoveryStopReason.REQUIRES_LOGIN,
        InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC: DiscoveryStopReason.DOCUMENT_NOT_PUBLIC,
        InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA: DiscoveryStopReason.INSUFFICIENT_PUBLIC_DATA,
        InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED: DiscoveryStopReason.MANUAL_REVIEW_REQUIRED,
    }
    try:
        return mapping[status]
    except KeyError as exc:
        raise ValueError(f"unsupported discovery status: {status.value}") from exc


@dataclass(frozen=True)
class InstitutionRegistryRecord:
    """Baseline institution row with explicit provenance and refresh state."""

    institution_id: str
    name_en: str
    regulator: InstitutionRegulator
    sector: InstitutionSector
    registry_source: str
    registry_source_url: str
    refresh_status: InstitutionRefreshStatus = InstitutionRefreshStatus.BASELINE_UNVERIFIED
    discovery_status: InstitutionDiscoveryStatus = InstitutionDiscoveryStatus.NOT_STARTED
    name_ar: Optional[str] = None
    country: str = "EG"
    official_website: Optional[str] = None
    official_website_confidence: float = 0.0
    attempt_count: int = 0
    last_checked_at: Optional[date] = None
    gap_reason: str = ""
    notes: str = ""
    baseline_inputs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.institution_id.strip():
            raise ValueError("institution_id is required")
        if not self.name_en.strip():
            raise ValueError("name_en is required")
        if self.regulator == InstitutionRegulator.UNKNOWN:
            raise ValueError("regulator provenance is required")
        if self.sector == InstitutionSector.UNKNOWN:
            raise ValueError("regulator category/sector is required")
        if not self.registry_source.strip():
            raise ValueError("registry_source is required")
        if not self.registry_source_url.startswith(("https://", "http://")):
            raise ValueError("registry_source_url must be an HTTP(S) URL")
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        if not 0.0 <= self.official_website_confidence <= 1.0:
            raise ValueError("official_website_confidence must be between 0 and 1")
        if self.discovery_status != InstitutionDiscoveryStatus.NOT_STARTED and self.attempt_count == 0:
            raise ValueError("discovery_status requires attempt_count")
        if self.discovery_status in {
            InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
            InstitutionDiscoveryStatus.SITE_UNREACHABLE,
            InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
            InstitutionDiscoveryStatus.REQUIRES_LOGIN,
            InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC,
            InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA,
            InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
        } and not self.gap_reason.strip():
            raise ValueError("gap_reason is required for non-success discovery gaps")

    @classmethod
    def baseline(
        cls,
        *,
        name_en: str,
        regulator: InstitutionRegulator,
        sector: InstitutionSector,
        registry_source: str,
        registry_source_url: str,
        **kwargs: object,
    ) -> "InstitutionRegistryRecord":
        return cls(
            institution_id=stable_institution_id(name_en, regulator, sector),
            name_en=name_en,
            regulator=regulator,
            sector=sector,
            registry_source=registry_source,
            registry_source_url=registry_source_url,
            **kwargs,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "InstitutionRegistryRecord":
        data = dict(payload)
        data["regulator"] = InstitutionRegulator(data["regulator"])
        data["sector"] = InstitutionSector(data["sector"])
        data["refresh_status"] = InstitutionRefreshStatus(
            data.get("refresh_status", InstitutionRefreshStatus.BASELINE_UNVERIFIED)
        )
        data["discovery_status"] = InstitutionDiscoveryStatus(
            data.get("discovery_status", InstitutionDiscoveryStatus.NOT_STARTED)
        )
        if isinstance(data.get("last_checked_at"), str):
            data["last_checked_at"] = date.fromisoformat(str(data["last_checked_at"]))
        return cls(**data)

    def to_dict(self) -> Dict[str, object]:
        return {
            "institution_id": self.institution_id,
            "name_en": self.name_en,
            "name_ar": self.name_ar,
            "country": self.country,
            "regulator": self.regulator.value,
            "sector": self.sector.value,
            "registry_source": self.registry_source,
            "registry_source_url": self.registry_source_url,
            "refresh_status": self.refresh_status.value,
            "discovery_status": self.discovery_status.value,
            "official_website": self.official_website,
            "official_website_confidence": self.official_website_confidence,
            "attempt_count": self.attempt_count,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "gap_reason": self.gap_reason,
            "notes": self.notes,
            "baseline_inputs": self.baseline_inputs,
        }


class InstitutionRegistry:
    """Strict in-memory registry for baseline and revalidated institutions."""

    def __init__(self, records: Iterable[InstitutionRegistryRecord] = ()) -> None:
        self._records: Dict[str, InstitutionRegistryRecord] = {}
        self._artifacts: Dict[str, PublicArtifactRecord] = {}
        self._operations: Dict[str, OperationCatalogRecord] = {}
        self._mappings: Dict[str, MachineAaoifiMappingCandidate] = {}
        self._reviews: Dict[str, ScholarReviewRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: InstitutionRegistryRecord) -> None:
        if record.institution_id in self._records:
            raise ValueError(f"duplicate institution_id: {record.institution_id}")
        self._records[record.institution_id] = record

    def get(self, institution_id: str) -> InstitutionRegistryRecord:
        try:
            return self._records[institution_id]
        except KeyError as exc:
            raise KeyError(f"unknown institution_id: {institution_id}") from exc

    def records(self) -> List[InstitutionRegistryRecord]:
        return list(self._records.values())

    def by_sector(self, sector: InstitutionSector) -> List[InstitutionRegistryRecord]:
        return [record for record in self._records.values() if record.sector == sector]

    def by_regulator(self, regulator: InstitutionRegulator) -> List[InstitutionRegistryRecord]:
        return [record for record in self._records.values() if record.regulator == regulator]

    def add_artifact(self, artifact: PublicArtifactRecord) -> None:
        self.get(artifact.institution_id)
        if artifact.artifact_id in self._artifacts:
            raise ValueError(f"duplicate artifact_id: {artifact.artifact_id}")
        self._artifacts[artifact.artifact_id] = artifact

    def artifacts_for(self, institution_id: str) -> List[PublicArtifactRecord]:
        self.get(institution_id)
        return [
            artifact
            for artifact in self._artifacts.values()
            if artifact.institution_id == institution_id
        ]

    def evidence_artifacts_for(self, institution_id: str) -> List[PublicArtifactRecord]:
        return [
            artifact
            for artifact in self.artifacts_for(institution_id)
            if artifact.authority_rank
            != PublicArtifactAuthorityRank.THIRD_PARTY_DISCOVERY_ONLY
            and artifact.extraction_status in {ExtractionStatus.EXTRACTED, ExtractionStatus.PARTIAL}
        ]

    def prioritized_artifacts_for(self, institution_id: str) -> List[PublicArtifactRecord]:
        return sorted(
            self.evidence_artifacts_for(institution_id),
            key=lambda artifact: artifact.priority_score,
            reverse=True,
        )

    def add_operation(self, operation: OperationCatalogRecord) -> None:
        self.get(operation.institution_id)
        for artifact_id in operation.artifact_ids:
            if artifact_id not in self._artifacts:
                raise KeyError(f"unknown artifact_id: {artifact_id}")
        if operation.operation_id in self._operations:
            raise ValueError(f"duplicate operation_id: {operation.operation_id}")
        self._operations[operation.operation_id] = operation

    def operations_for(self, institution_id: str) -> List[OperationCatalogRecord]:
        self.get(institution_id)
        return [
            operation
            for operation in self._operations.values()
            if operation.institution_id == institution_id
        ]

    def add_machine_mapping(self, mapping: MachineAaoifiMappingCandidate) -> None:
        if mapping.operation_id not in self._operations:
            raise KeyError(f"unknown operation_id: {mapping.operation_id}")
        if mapping.mapping_id in self._mappings:
            raise ValueError(f"duplicate mapping_id: {mapping.mapping_id}")
        self._mappings[mapping.mapping_id] = mapping

    def add_scholar_review(self, review: ScholarReviewRecord) -> None:
        if review.mapping_id not in self._mappings:
            raise KeyError(f"unknown mapping_id: {review.mapping_id}")
        if review.review_id in self._reviews:
            raise ValueError(f"duplicate review_id: {review.review_id}")
        self._reviews[review.review_id] = review

    def accepted_gold_reviews(self) -> List[ScholarReviewRecord]:
        return [
            review
            for review in self._reviews.values()
            if review.accepted_gold_case and review.decision == ReviewCandidateStatus.SCHOLAR_ACCEPTED
        ]

    def with_discovery_result(
        self,
        result: OfficialSiteDiscoveryResult,
    ) -> "InstitutionRegistry":
        record = self.get(result.institution_id)
        updates = result.to_registry_updates()
        updated = InstitutionRegistryRecord(
            institution_id=record.institution_id,
            name_en=record.name_en,
            regulator=record.regulator,
            sector=record.sector,
            registry_source=record.registry_source,
            registry_source_url=record.registry_source_url,
            refresh_status=record.refresh_status,
            discovery_status=updates["discovery_status"],
            name_ar=record.name_ar,
            country=record.country,
            official_website=updates["official_website"],
            official_website_confidence=updates["official_website_confidence"],
            attempt_count=updates["attempt_count"],
            last_checked_at=updates["last_checked_at"],
            gap_reason=updates["gap_reason"],
            notes=record.notes,
            baseline_inputs=record.baseline_inputs,
        )
        return InstitutionRegistry(
            updated if item.institution_id == updated.institution_id else item
            for item in self._records.values()
        )

    @classmethod
    def from_payload(cls, records: Iterable[Mapping[str, object]]) -> "InstitutionRegistry":
        return cls(InstitutionRegistryRecord.from_mapping(record) for record in records)
