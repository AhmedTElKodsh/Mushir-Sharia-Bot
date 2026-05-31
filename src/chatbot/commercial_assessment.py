"""Deterministic L6 scaffolding for commercial-process assessment.

This module does not issue Sharia verdicts. It extracts a conservative
transaction scenario, chooses source-family routing, and flags cases where the
current FAS-heavy evidence layer is not enough for permissibility assessment.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Set

from src.chatbot.contract_classifier import ContractTypeClassifier
from src.governance.router_seed import RouterSeedRecord, RouterSeedRegistry, default_router_seed_registry
from src.models.commercial import (
    ContractFamily,
    QuestionType,
    RuleEvaluation,
    SourceFamily,
    StandardsRoute,
    TransactionScenario,
    VerdictContract,
    VerdictStatus,
)
from src.ontology import ConceptOntologyRouter

AR_MURABAHA = "\u0645\u0631\u0627\u0628\u062d\u0629"
AR_MURABAHA_ALT = "\u0645\u0631\u0627\u0628\u062d\u0647"
AR_INSTALLMENT = "\u062a\u0642\u0633\u064a\u0637"
AR_INSTALLMENT_WITH_B = "\u0628\u0627\u0644\u062a\u0642\u0633\u064a\u0637"
AR_CAR_1 = "\u0633\u064a\u0627\u0631\u0629"
AR_CAR_2 = "\u0639\u0631\u0628\u064a\u0629"
AR_HALAL = "\u062d\u0644\u0627\u0644"
AR_HARAM = "\u062d\u0631\u0627\u0645"
AR_ALLOWED = "\u064a\u062c\u0648\u0632"
AR_VALID = "\u062c\u0627\u0626\u0632"
AR_RULING = "\u062d\u0643\u0645"
AR_COMPLIANT = "\u0645\u062a\u0648\u0627\u0641\u0642"
AR_OK = "\u064a\u0646\u0641\u0639"
AR_SHARIA_ADJECTIVE = "\u0634\u0631\u0639\u064a"
AR_MATCHING = "\u0645\u0637\u0627\u0628\u0642"
AR_LATE_1 = "\u063a\u0631\u0627\u0645\u0629"
AR_LATE_2 = "\u062a\u0623\u062e\u064a\u0631"
AR_LATE_3 = "\u062a\u0627\u062e\u064a\u0631"
AR_LATE_4 = "\u062a\u0622\u062e\u064a\u0631"
AR_LATE_COMPENSATION = "\u062a\u0639\u0648\u064a\u0636"
AR_LATE_INTEREST = "\u0641\u0648\u0627\u0626\u062f \u062a\u0623\u062e\u064a\u0631"
AR_RIBA = "\u0631\u0628\u0627"
AR_RIBAWI = "\u0631\u0628\u0648\u064a"
AR_CUSTOMER = "\u0639\u0645\u064a\u0644"
AR_INSTALLMENT_PAYMENT = "\u0642\u0633\u0637"
AR_CASH = "\u0646\u0642\u062f"
AR_CONSTRUCTION_TERMS = (
    "\u0645\u0642\u0627\u0648\u0644\u0627\u062a",
    "\u0645\u0642\u0627\u0648\u0644\u0629",
    "\u0645\u0642\u0627\u0648\u0644",
    "\u0625\u0646\u0634\u0627\u0621\u0627\u062a",
    "\u0627\u0646\u0634\u0627\u0621\u0627\u062a",
    "\u062a\u0634\u064a\u064a\u062f",
)
AR_SUPPLY_TERMS = ("\u062a\u0648\u0631\u064a\u062f", "\u0645\u0648\u0631\u062f")
AR_MANUFACTURING_TERMS = ("\u062a\u0635\u0646\u064a\u0639", "\u0645\u0635\u0646\u0639", "\u0635\u0627\u0646\u0639", "\u0627\u0633\u062a\u0635\u0646\u0627\u0639")
AR_CHARITY_TERMS = (
    "\u062c\u0647\u0629 \u062e\u064a\u0631\u064a\u0629",
    "\u0623\u0639\u0645\u0627\u0644 \u062e\u064a\u0631\u064a\u0629",
    "\u0627\u0639\u0645\u0627\u0644 \u062e\u064a\u0631\u064a\u0629",
    "\u062e\u064a\u0631\u064a\u0629",
    "\u062e\u064a\u0631\u0649",
    "\u062a\u0628\u0631\u0639",
    "\u062a\u0628\u0631\u0639\u0627\u062a",
)


class ScenarioExtractor:
    """Small deterministic extractor for first-wave commercial domains."""

    def __init__(self, contract_classifier: Optional[ContractTypeClassifier] = None) -> None:
        self._contract_classifier = contract_classifier or ContractTypeClassifier()

    _PERMISSIBILITY_TERMS = (
        "halal", "haram", "riba", "ribawi", "permissible", "allowed", "valid", "sharia-compliant",
        "compliant", "ruling", "can i ", "can we ", "should i ", "should we ",
        "is it ok", "is it okay", "acceptable", "islamically",
        AR_HALAL, AR_HARAM, AR_ALLOWED, AR_VALID, AR_RULING, AR_COMPLIANT,
        AR_OK, AR_SHARIA_ADJECTIVE, AR_MATCHING,
    )
    _ACCOUNTING_TERMS = (
        "accounting", "recognition", "measurement", "presentation", "disclosure",
        "reporting", "journal entry", "\u0645\u0639\u0627\u0644\u062c\u0629",
        "\u0625\u0641\u0635\u0627\u062d", "\u0642\u064a\u0627\u0633",
        "\u0627\u0639\u062a\u0631\u0627\u0641",
    )
    _GOVERNANCE_TERMS = (
        "governance", "audit", "board", "policy",
        "\u062d\u0648\u0643\u0645\u0629", "\u062a\u062f\u0642\u064a\u0642",
    )
    _LATE_PENALTY_TERMS = (
        "late fee", "late payment", "delayed payment", "penalty",
        "default charge", "default fee", "collection cost", "grace period",
        "delays payment", "delayed payments", "liquidated damages",
        "delay damages", "delay damage", "ld clause", "lds",
        "late delivery damages", "late completion damages", "fidic delay",
        "fidic damages", "fidic penalty",
        AR_LATE_1, "\u063a\u0631\u0627\u0645\u0647", AR_LATE_2, AR_LATE_3,
        AR_LATE_4,
        AR_LATE_COMPENSATION, AR_LATE_INTEREST,
        "\u0634\u0631\u0637 \u062c\u0632\u0627\u0626\u064a",
        "\u0627\u0644\u0634\u0631\u0637 \u0627\u0644\u062c\u0632\u0627\u0626\u064a",
        "\u062a\u0639\u0648\u064a\u0636 \u062a\u0623\u062e\u064a\u0631",
        "\u0641\u0644\u0648\u0633 \u0632\u064a\u0627\u062f\u0629",
        "\u0627\u062a\u0623\u062e\u0631\u062a", "\u0627\u062a\u0627\u062e\u0631\u062a",
    )

    def extract(self, query: str) -> TransactionScenario:
        text = query or ""
        lowered = text.lower()
        classification = self._contract_classifier.classify(text)
        contract_family = classification.contract_family if classification else self._contract_family(lowered)
        question_type = self._question_type(lowered)
        if question_type == QuestionType.PERMISSIBILITY and not self._has_commercial_context(lowered, contract_family):
            question_type = QuestionType.UNKNOWN
        scenario = TransactionScenario(
            question_type=question_type,
            contract_family=contract_family,
        )
        scenario.asset = self._asset(text, lowered)
        scenario.payment_terms = self._payment_terms(text, lowered)
        scenario.late_payment_terms = self._late_payment_terms(text, lowered)
        scenario.profit_basis = self._profit_basis(text, lowered)
        scenario.ownership_sequence = self._sequence_fact(text, lowered, "ownership")
        scenario.possession_sequence = self._sequence_fact(text, lowered, "possession")
        scenario.risk_bearing = self._sequence_fact(text, lowered, "risk")
        scenario.penalty_beneficiary = self._penalty_beneficiary(lowered)
        scenario.missing_facts = self._missing_facts(scenario)
        scenario.uncertainties = self._uncertainties(scenario)
        return scenario

    def _question_type(self, lowered: str) -> QuestionType:
        hard_permissibility_terms = (
            "halal", "haram", "riba", "ribawi", "permissible", "allowed", "valid",
            "sharia-compliant", "can ", "can i ", "can we ", "should i ", "should we ",
            "should the bank", "should a bank", "should the customer",
            "is it ok", "is it okay", "acceptable", "islamically",
            AR_HALAL, AR_HARAM, AR_ALLOWED, AR_VALID, AR_OK,
            AR_SHARIA_ADJECTIVE, AR_MATCHING, AR_RIBA, AR_RIBAWI, "\u0631\u0628\u0648\u064a\u0629",
        )
        if any(term in lowered for term in hard_permissibility_terms):
            return QuestionType.PERMISSIBILITY
        if any(term in lowered for term in self._ACCOUNTING_TERMS):
            return QuestionType.ACCOUNTING
        if any(term in lowered for term in self._GOVERNANCE_TERMS):
            return QuestionType.GOVERNANCE
        if any(term in lowered for term in self._PERMISSIBILITY_TERMS):
            return QuestionType.PERMISSIBILITY
        if lowered.startswith(("what is ", "define ", "explain ", "\u0645\u0627 \u0647\u064a ", "\u0645\u0627 \u0647\u0648 ")):
            return QuestionType.EXPLANATION
        return QuestionType.UNKNOWN

    @staticmethod
    def _has_commercial_context(lowered: str, contract_family: ContractFamily) -> bool:
        if contract_family != ContractFamily.UNKNOWN:
            return True
        commercial_terms = (
            "bank", "financier", "customer", "borrower", "seller", "buyer",
            "loan", "financing", "finance", "investment", "stock", "shares",
            "company", "business", "contract", "agreement", "purchase", "buy",
            "bought", "sell", "sale", "asset", "car", "vehicle", "property",
            "real estate", "installment", "instalment", "deferred", "markup",
            "mark-up", "profit", "late fee", "late payment", "penalty",
            "fee", "payment", "charge", "default", "guarantee", "capital",
            "receivable", "undertaking", "promise", "buyback", "discount",
            "reschedule", "agency", "agent", "collateral", "insurance",
            "construction", "contractor", "contracting", "muqawala", "supply",
            "supplier", "manufacturing", "manufacturer", "industrial",
            "liquidated damages", "delay damages", "ld clause", "fidic",
            "currency", "fx", "foreign exchange", "sarf", "settle", "settlement",
            "\u0628\u0646\u0643", "\u0645\u0635\u0631\u0641", "\u0642\u0631\u0636",
            "\u062a\u0645\u0648\u064a\u0644", "\u0627\u0633\u062a\u062b\u0645\u0627\u0631",
            "\u0623\u0633\u0647\u0645", "\u0634\u0631\u0643\u0629", "\u0639\u0642\u062f",
            "\u0634\u0631\u0627\u0621", "\u0627\u0634\u062a\u0631\u064a\u062a",
            "\u0628\u064a\u0639", AR_CAR_1, AR_CAR_2, AR_INSTALLMENT,
            AR_INSTALLMENT_WITH_B, "\u0631\u0628\u062d", AR_LATE_1, AR_LATE_2,
            AR_LATE_3, "\u0639\u0645\u064a\u0644", "\u062f\u0641\u0639",
            "\u0642\u0633\u0637", "\u0623\u0642\u0633\u0627\u0637", "\u0627\u0642\u0633\u0627\u0637",
            "\u0636\u0645\u0627\u0646", "\u0648\u0639\u062f", "\u0648\u0643\u0627\u0644\u0629",
            "\u0631\u0647\u0646", "\u062a\u0623\u0645\u064a\u0646",
            "\u0634\u0631\u0637 \u062c\u0632\u0627\u0626\u064a",
            "\u0639\u0645\u0644\u0629", "\u0635\u0631\u0641", "\u062a\u0633\u0648\u064a\u0629",
            *AR_CONSTRUCTION_TERMS, *AR_SUPPLY_TERMS, *AR_MANUFACTURING_TERMS,
        )
        return any(term in lowered for term in commercial_terms)

    @staticmethod
    def _contract_family(lowered: str) -> ContractFamily:
        checks = (
            (ContractFamily.MURABAHA, ("murabaha", "murabahah", AR_MURABAHA, AR_MURABAHA_ALT)),
            (ContractFamily.IJARAH, ("ijarah", "ijara", "lease", "\u0625\u062c\u0627\u0631\u0629", "\u0627\u064a\u062c\u0627\u0631")),
            (ContractFamily.TAWARRUQ, ("tawarruq", "\u062a\u0648\u0631\u0642")),
            (ContractFamily.QARD, ("qard", "loan", "interest", "cash advance", "\u0642\u0631\u0636", "\u0641\u0627\u0626\u062f\u0629", "\u0641\u0648\u0627\u0626\u062f", AR_CASH)),
            (ContractFamily.WAKALA, ("wakala", "agency", "\u0648\u0643\u0627\u0644\u0629")),
            (ContractFamily.SUKUK, ("sukuk", "\u0635\u0643\u0648\u0643")),
            (ContractFamily.MUSHARAKA, ("musharaka", "musharakah", "\u0645\u0634\u0627\u0631\u0643\u0629")),
            (ContractFamily.MUDARABA, ("mudaraba", "mudarabah", "\u0645\u0636\u0627\u0631\u0628\u0629")),
            (ContractFamily.SALAM, ("salam", "\u0633\u0644\u0645")),
            (ContractFamily.ISTISNA, ("istisna", "istisna'a", "istisna’a", "construction", "contractor", "contracting", "muqawala", "fidic", "manufacturing", "manufactured", "\u0627\u0633\u062a\u0635\u0646\u0627\u0639", *AR_CONSTRUCTION_TERMS)),
        )
        for family, terms in checks:
            if any(term in lowered for term in terms):
                return family
        if any(term in lowered for term in ("installment", "instalment", AR_INSTALLMENT, AR_INSTALLMENT_WITH_B)):
            return ContractFamily.MURABAHA
        if "buy now pay later" in lowered or "bnpl" in lowered:
            return ContractFamily.MURABAHA
        if any(term in lowered for term in AR_SUPPLY_TERMS + AR_MANUFACTURING_TERMS):
            return ContractFamily.ISTISNA
        return ContractFamily.UNKNOWN

    @staticmethod
    def _asset(text: str, lowered: str) -> Optional[str]:
        if any(term in lowered for term in ("car", "vehicle", AR_CAR_1, AR_CAR_2)):
            return "car"
        match = re.search(r"\b(?:buy|purchase|bought)\s+(?:a|an|the)?\s*([a-z][a-z -]{2,40})", text, re.IGNORECASE)
        return match.group(1).strip(" .,-") if match else None

    @staticmethod
    def _payment_terms(text: str, lowered: str) -> Optional[str]:
        markers = (
            "installment", "instalment", "deferred", "monthly", "years", "months",
            AR_INSTALLMENT, "\u062f\u0641\u0639\u0629", "\u0623\u0642\u0633\u0627\u0637",
            "\u0633\u0646\u0648\u0627\u062a",
        )
        return text if any(marker in lowered for marker in markers) else None

    def _late_payment_terms(self, text: str, lowered: str) -> Optional[str]:
        return text if any(term in lowered for term in self._LATE_PENALTY_TERMS) else None

    @staticmethod
    def _profit_basis(text: str, lowered: str) -> Optional[str]:
        if any(term in lowered for term in ("markup", "mark-up", "profit", "\u0631\u0628\u062d", "\u0642\u064a\u0645\u0629 \u0645\u0636\u0627\u0641\u0629")):
            percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            return f"{percent.group(1)}%" if percent else text
        return None

    @staticmethod
    def _sequence_fact(text: str, lowered: str, kind: str) -> Optional[str]:
        terms = {
            "ownership": ("ownership", "owns", "owned", "\u062a\u0645\u0644\u0643", "\u0645\u0644\u0643"),
            "possession": ("possession", "possess", "delivery", "\u0642\u0628\u0636", "\u062d\u064a\u0627\u0632\u0629", "\u062a\u0633\u0644\u064a\u0645"),
            "risk": ("risk", "liability", "\u0645\u062e\u0627\u0637\u0631", "\u0636\u0645\u0627\u0646"),
        }[kind]
        return text if any(term in lowered for term in terms) else None

    @staticmethod
    def _penalty_beneficiary(lowered: str) -> Optional[str]:
        if any(ScenarioExtractor._contains_phrase_or_word(lowered, term) for term in ("charity", "donation", *AR_CHARITY_TERMS)):
            return "charity"
        if any(term in lowered for term in ("bank receives", "lender receives", "\u0644\u0644\u0628\u0646\u0643")):
            return "financier"
        return None

    @staticmethod
    def _contains_phrase_or_word(text: str, term: str) -> bool:
        if " " in term:
            return term in text
        if any("\u0600" <= char <= "\u06ff" for char in term):
            return bool(re.search(rf"(?<![\u0600-\u06ff]){re.escape(term)}(?![\u0600-\u06ff])", text))
        return bool(re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE))

    @staticmethod
    def _missing_facts(scenario: TransactionScenario) -> List[str]:
        missing: List[str] = []
        if scenario.question_type == QuestionType.PERMISSIBILITY and scenario.contract_family == ContractFamily.MURABAHA:
            if not scenario.ownership_sequence:
                missing.append("ownership_sequence")
            if not scenario.possession_sequence and not scenario.risk_bearing:
                missing.append("possession_or_risk_bearing")
            if scenario.late_payment_terms and not scenario.penalty_beneficiary:
                missing.append("penalty_beneficiary")
        if (
            scenario.question_type == QuestionType.PERMISSIBILITY
            and scenario.contract_family == ContractFamily.ISTISNA
            and scenario.late_payment_terms
        ):
            if not ScenarioExtractor._known_istisna_delay_party(scenario.late_payment_terms):
                missing.append("delay_responsible_party")
            missing.append("penalty_trigger")
            missing.append("force_majeure_or_actual_loss_context")
        return missing

    @staticmethod
    def _known_istisna_delay_party(text: str) -> bool:
        lowered = (text or "").lower()
        contractor_terms = (
            "contractor is late",
            "contractor was late",
            "contractor delays",
            "contractor delay",
            "contractor delayed",
            "late delivering",
            "late delivery",
            "late completion",
            "delays handover",
            "\u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0642\u0627\u0648\u0644",
            "\u062a\u0627\u062e\u0631 \u0627\u0644\u0645\u0642\u0627\u0648\u0644",
            "\u062a\u0623\u062e\u0631 \u0627\u0644\u0635\u0627\u0646\u0639",
            "\u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0648\u0631\u062f",
        )
        customer_terms = (
            "customer is late paying",
            "customer was late paying",
            "customer delays payment",
            "client delays payment",
            "late paying",
            "late payment by customer",
            "\u062a\u0623\u062e\u0631 \u0627\u0644\u0639\u0645\u064a\u0644",
            "\u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u0634\u062a\u0631\u064a",
        )
        return any(term in lowered for term in contractor_terms + customer_terms)

    @staticmethod
    def _uncertainties(scenario: TransactionScenario) -> List[str]:
        uncertainties: List[str] = []
        if scenario.question_type == QuestionType.PERMISSIBILITY:
            uncertainties.append("permissibility_requires_sharia_standards")
        if scenario.late_payment_terms:
            uncertainties.append("late_payment_penalty_requires_dedicated_rule_check")
        if scenario.contract_family == ContractFamily.ISTISNA and scenario.late_payment_terms:
            uncertainties.append("penalty_clause_context_requires_party_and_delay_type")
        return uncertainties


class StandardsRouter:
    """Choose source-family routes from the extracted scenario."""

    def __init__(
        self,
        seed_registry: Optional[RouterSeedRegistry] = None,
        ontology_router: Optional[ConceptOntologyRouter] = None,
    ) -> None:
        self._seed_registry = seed_registry or default_router_seed_registry()
        self._ontology_router = ontology_router or ConceptOntologyRouter()

    def route(self, scenario: TransactionScenario, query: str = "") -> StandardsRoute:
        seed = self._seed_registry.match(query) if query else None
        if scenario.question_type == QuestionType.ACCOUNTING:
            return StandardsRoute(
                primary=seed.source_families if seed else [SourceFamily.FAS],
                secondary=[SourceFamily.GOVERNANCE],
                candidate_standards=seed.candidate_standards if seed else [],
                route_id=seed.route_id if seed else None,
                rationale="Accounting, recognition, measurement, presentation, or disclosure question.",
                requires_rule_evaluation=False,
            )
        if scenario.question_type == QuestionType.PERMISSIBILITY:
            route_id, candidate_standards = self._hard_sharia_route(scenario, query, seed)
            ontology_route = self._ontology_router.route_query(query, scenario.contract_family)
            if ontology_route.standard_ids and not candidate_standards:
                candidate_standards = sorted(set(candidate_standards) | set(ontology_route.standard_ids))
            return StandardsRoute(
                primary=[SourceFamily.SHARIA_STANDARD],
                secondary=[SourceFamily.FAS, SourceFamily.GOVERNANCE],
                candidate_standards=candidate_standards,
                route_id=route_id,
                rationale="Permissibility and contract-validity questions require Shari'ah-source routing before FAS accounting support.",
                requires_rule_evaluation=scenario.contract_family != ContractFamily.UNKNOWN,
            )
        return StandardsRoute(
            primary=seed.source_families if seed else [SourceFamily.FAS],
            secondary=[],
            candidate_standards=seed.candidate_standards if seed else [],
            route_id=seed.route_id if seed else None,
            rationale="Default informational route over the currently indexed corpus.",
            requires_rule_evaluation=False,
        )

    @staticmethod
    def _hard_sharia_route(
        scenario: TransactionScenario,
        query: str,
        seed: Optional[RouterSeedRecord],
    ) -> tuple[Optional[str], List[str]]:
        lowered = (query or "").lower()
        if scenario.late_payment_terms and scenario.contract_family == ContractFamily.ISTISNA:
            return "istisna-penalty-clause", ["SS-05", "SS-11"]
        if scenario.late_payment_terms and scenario.contract_family == ContractFamily.MURABAHA:
            return "murabaha-late-payment-penalty", ["SS-03", "SS-08"]
        if scenario.late_payment_terms and scenario.contract_family == ContractFamily.QARD:
            return "debt-late-payment-penalty", ["SS-03", "SS-19"]
        if StandardsRouter._has_currency_exchange_signal(lowered):
            return "currency-sarf-settlement", ["SS-01"]
        if any(term in lowered for term in ("guarantee", "kafalah", "ضمان", "كفالة")):
            if scenario.contract_family == ContractFamily.MUDARABA:
                return "mudaraba-guarantee", ["SS-13", "SS-05"]
            return "guarantee-kafalah-fee", ["SS-05"]
        if any(term in lowered for term in ("sale of debt", "بيع الدين")):
            return "debt-sale", ["SS-60"]
        if any(term in lowered for term in ("bay' al-wafa", "sale with right of redemption", "بيع الوفاء")):
            return "bay-al-wafa", ["OIC-40"]
        if scenario.contract_family == ContractFamily.ISTISNA and any(term in lowered for term in ("software", "برمجيات", "services", "خدمات", "maintenance", "صيانة")):
            return "istisna-services", ["SS-11", "SS-09"]
        if any(term in lowered for term in ("takaful", "insurance", "تأمين", "تكافلي")):
            return "takaful-insurance", ["SS-26"]
        if any(term in lowered for term in ("real estate financing", "التمويل العقاري")):
            return "real-estate-financing", ["SS-09", "SS-14"]
        family_routes = {
            ContractFamily.MURABAHA: ("murabaha-permissibility", ["SS-08"]),
            ContractFamily.IJARAH: ("ijarah-permissibility", ["SS-09"]),
            ContractFamily.SALAM: ("salam-permissibility", ["SS-10"]),
            ContractFamily.ISTISNA: ("istisna-permissibility", ["SS-11"]),
            ContractFamily.TAWARRUQ: ("tawarruq-permissibility", ["SS-30"]),
            ContractFamily.QARD: ("qard-permissibility", ["SS-19"]),
            ContractFamily.KAFALA: ("guarantee-kafalah-fee", ["SS-05"]),
            ContractFamily.WAKALA: ("wakala-permissibility", ["SS-46"]),
            ContractFamily.SUKUK: ("sukuk-permissibility", ["SS-17"]),
            ContractFamily.MUSHARAKA: ("musharaka-permissibility", ["SS-12"]),
            ContractFamily.MUDARABA: ("mudaraba-permissibility", ["SS-13"]),
        }
        if scenario.contract_family in family_routes:
            return family_routes[scenario.contract_family]
        if seed:
            sharia_candidates = [
                standard
                for standard in seed.candidate_standards
                if re.match(r"^SS[-_\s]?\d+", standard.strip(), flags=re.IGNORECASE)
            ]
            return (seed.route_id if sharia_candidates else None), sharia_candidates
        return None, []

    @staticmethod
    def _has_currency_exchange_signal(lowered_query: str) -> bool:
        english_terms = ("currency", "fx", "foreign exchange", "sarf")
        if any(term in lowered_query for term in english_terms):
            return True
        arabic_letter = r"\u0600-\u06ff"
        return bool(
            re.search(rf"(?<![{arabic_letter}])\u0635\u0631\u0641(?![{arabic_letter}])", lowered_query)
            or re.search(r"\u0639\u0645\u0644(?:\u0629|\u0627\u062a)", lowered_query)
        )


class CommercialRuleEvaluator:
    """Conservative deterministic rule traces for first-wave commercial domains."""

    MURABAHA_LATE_PAYMENT_RULE_ID = "murabaha-late-payment-v1"
    ISTISNA_CONSTRUCTION_PENALTY_RULE_ID = "istisna-construction-penalty-v1"
    RULE_VERSION = "2026-05-24"

    def evaluate(self, scenario: TransactionScenario, route: StandardsRoute) -> RuleEvaluation:
        required = list(scenario.missing_facts)
        flags: List[str] = []
        evidence_requirements: List[str] = []
        matched_rules: List[str] = []
        rule_id: Optional[str] = None
        rule_version: Optional[str] = None

        if (
            scenario.contract_family == ContractFamily.MURABAHA
            and scenario.late_payment_terms
            and route.requires_rule_evaluation
        ):
            rule_id = self.MURABAHA_LATE_PAYMENT_RULE_ID
            rule_version = self.RULE_VERSION
            matched_rules.append(rule_id)
            evidence_requirements.extend(
                [
                    "sharia_standard_evidence",
                    "penalty_beneficiary",
                    "ownership_sequence",
                    "possession_or_risk_bearing",
                ]
            )
            flags.append("human_review_required")
            flags.append("late_payment_penalty_review_required")
        if (
            scenario.contract_family == ContractFamily.ISTISNA
            and scenario.late_payment_terms
            and route.requires_rule_evaluation
        ):
            rule_id = self.ISTISNA_CONSTRUCTION_PENALTY_RULE_ID
            rule_version = self.RULE_VERSION
            matched_rules.append(rule_id)
            evidence_requirements.extend(
                [
                    "sharia_standard_evidence",
                    "delay_responsible_party",
                    "penalty_trigger",
                    "force_majeure_or_actual_loss_context",
                ]
            )
            flags.append("human_review_required")
            flags.append("penalty_clause_review_required")
        if route.requires_rule_evaluation:
            flags.append("source_governed_rule_trace_required")
        if scenario.late_payment_terms:
            if "late_payment_penalty_review_required" not in flags:
                flags.append("late_payment_penalty_review_required")
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=rule_version,
            matched_rules=matched_rules,
            required_facts=required,
            missing_facts=required,
            evidence_requirements=evidence_requirements,
            outcome="unknown",
            conflict_flags=[],
            human_review_flags=flags,
        )


class EvidenceFamilyDetector:
    """Infer source families from retrieved chunks."""

    MIN_RELEVANCE_SCORE = 0.30

    @classmethod
    def families(cls, chunks: Iterable[Any]) -> Set[SourceFamily]:
        return {cls.family_for_chunk(chunk) for chunk in chunks}

    @classmethod
    def family_for_chunk(cls, chunk: Any) -> SourceFamily:
        score = getattr(chunk, "score", None)
        if score is None and isinstance(chunk, dict):
            score = chunk.get("score")
        if score is not None and score < cls.MIN_RELEVANCE_SCORE:
            return SourceFamily.UNKNOWN

        metadata = cls._metadata(chunk)
        explicit_family = str(metadata.get("source_family") or "").strip().lower()
        for family in SourceFamily:
            if explicit_family == family.value:
                return family
        raw = " ".join(
            str(metadata.get(key, ""))
            for key in ("source_family", "standard_type", "standard_number", "source_file", "document_id")
        ).lower()
        citation = getattr(chunk, "citation", None)
        source_file = str(getattr(citation, "source_file", "")).lower()
        standard_id = str(getattr(citation, "standard_id", "")).lower()
        raw = f"{raw} {standard_id} {source_file}"
        if cls._has_sharia_standard_marker(raw, standard_id, source_file):
            return SourceFamily.SHARIA_STANDARD
        if "governance" in raw or "gs-" in raw:
            return SourceFamily.GOVERNANCE
        if "ethic" in raw:
            return SourceFamily.ETHICS
        if "audit" in raw:
            return SourceFamily.AUDITING
        if "fatwa" in raw:
            return SourceFamily.FATWA
        if "fas" in raw or "financial_accounting" in raw:
            return SourceFamily.FAS
        return SourceFamily.UNKNOWN

    @staticmethod
    def _has_sharia_standard_marker(raw: str, standard_id: str, source_file: str) -> bool:
        if standard_id.startswith(("ss-", "ss_", "sharia-")):
            return True
        if "sharia" in source_file or "shari" in source_file:
            return True
        if "sharia_standard" in raw and ("ss-" in raw or "ss_" in raw):
            return True
        return False

    @staticmethod
    def _metadata(chunk: Any) -> dict:
        if isinstance(chunk, dict):
            return chunk.get("metadata", {}) or {}
        return getattr(chunk, "metadata", {}) or {}


def should_fail_closed_for_source_gap(
    scenario: TransactionScenario,
    route: StandardsRoute,
    evidence_families: Set[SourceFamily],
) -> bool:
    """Return True when the current evidence cannot support a safe verdict."""
    if scenario.question_type != QuestionType.PERMISSIBILITY:
        return False
    if SourceFamily.SHARIA_STANDARD not in route.primary:
        return False
    if SourceFamily.SHARIA_STANDARD in evidence_families:
        return False
    return True


def source_gap_verdict(
    scenario: TransactionScenario,
    route: StandardsRoute,
    evidence_families: Set[SourceFamily],
) -> VerdictContract:
    return VerdictContract(
        verdict=VerdictStatus.REFER_TO_SCHOLAR,
        confidence=0.0,
        evidence=sorted(family.value for family in evidence_families),
        standards_used=[],
        rule_path=["scenario_extraction", "standards_routing", "source_family_gap"],
        limitations=[
            "Permissibility questions require Shari'ah-standard evidence.",
            "The current retrieved evidence did not include a Shari'ah-standard source family.",
            "Late-payment/default clauses require dedicated rule and scholar review.",
        ],
        requires_scholar_review=True,
    )
