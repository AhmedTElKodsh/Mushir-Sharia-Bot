"""Reviewable first-release router seeds for accounting-standard routing."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set

from src.models.commercial import ContractFamily, QuestionType, SourceFamily
from src.rag.query_preprocessor import QueryPreprocessor


class RouterSeedStatus(str, Enum):
    UNVERIFIED = "unverified"
    CATALOG_VERIFIED = "catalog_verified"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RouterSeedRecord:
    """Candidate concept-to-standard route pending catalog verification."""

    route_id: str
    canonical_concept: str
    contract_family: ContractFamily
    question_types: List[QuestionType]
    source_families: List[SourceFamily]
    candidate_standards: List[str]
    terms_en: List[str] = field(default_factory=list)
    terms_ar: List[str] = field(default_factory=list)
    transliterations: List[str] = field(default_factory=list)
    status: RouterSeedStatus = RouterSeedStatus.UNVERIFIED
    ambiguity_warning: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.route_id.strip():
            raise ValueError("route_id is required")
        if not self.canonical_concept.strip():
            raise ValueError("canonical_concept is required")
        if not self.question_types:
            raise ValueError("question_types is required")
        if not self.source_families:
            raise ValueError("source_families is required")
        if not self.candidate_standards:
            raise ValueError("candidate_standards is required")

    def terms(self) -> Set[str]:
        values = self.terms_en + self.terms_ar + self.transliterations + [self.canonical_concept]
        return {QueryPreprocessor.normalize(term).lower() for term in values if term.strip()}

    @property
    def allows_retrieval(self) -> bool:
        return self.status in {RouterSeedStatus.UNVERIFIED, RouterSeedStatus.CATALOG_VERIFIED}

    @property
    def is_catalog_verified(self) -> bool:
        return self.status == RouterSeedStatus.CATALOG_VERIFIED


class RouterSeedRegistry:
    """Lookup registry for reviewable route seed records."""

    def __init__(self, records: Iterable[RouterSeedRecord]) -> None:
        self._records = list(records)
        self._by_id: Dict[str, RouterSeedRecord] = {}
        for record in self._records:
            if record.route_id in self._by_id:
                raise ValueError(f"duplicate route_id: {record.route_id}")
            self._by_id[record.route_id] = record

    def get(self, route_id: str) -> RouterSeedRecord:
        try:
            return self._by_id[route_id]
        except KeyError as exc:
            raise KeyError(f"unknown route_id: {route_id}") from exc

    def match(self, query: str) -> Optional[RouterSeedRecord]:
        normalized = QueryPreprocessor.normalize(query).lower()
        expanded = QueryPreprocessor.expand_terms(query)
        for record in self._records:
            if record.status == RouterSeedStatus.REJECTED:
                continue
            if any(term in normalized or term in expanded for term in record.terms()):
                return record
        return None

    def verified_routes_for(self, source_family: SourceFamily) -> List[RouterSeedRecord]:
        return [
            record
            for record in self._records
            if record.is_catalog_verified and source_family in record.source_families
        ]


def default_router_seed_registry(extra_records: Iterable[RouterSeedRecord] = ()) -> RouterSeedRegistry:
    """Return unverified accounting-route seeds from the 2026-05-19 plan."""
    zakah_ar = "\u0632\u0643\u0627\u0629"
    takaful_ar = "\u062a\u0643\u0627\u0641\u0644"
    sukuk_ar = "\u0635\u0643\u0648\u0643"
    shares_ar = "\u0623\u0633\u0647\u0645"

    seeds = [
        RouterSeedRecord(
            route_id="murabaha-accounting",
            canonical_concept="murabaha",
            contract_family=ContractFamily.MURABAHA,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-28"],
            terms_en=["murabaha", "murabahah", "deferred payment sale", "cost-plus sale"],
            terms_ar=["\u0645\u0631\u0627\u0628\u062d\u0629", "\u0627\u0644\u0645\u0631\u0627\u0628\u062d\u0629"],
            ambiguity_warning="FAS route is accounting support only; permissibility requires Shariah sources.",
        ),
        RouterSeedRecord(
            route_id="salam-accounting",
            canonical_concept="salam",
            contract_family=ContractFamily.SALAM,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-7"],
            terms_en=["salam", "parallel salam"],
            terms_ar=["\u0633\u0644\u0645", "\u0627\u0644\u0633\u0644\u0645"],
        ),
        RouterSeedRecord(
            route_id="istisna-accounting",
            canonical_concept="istisna",
            contract_family=ContractFamily.ISTISNA,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-10"],
            terms_en=["istisna", "istisna'a", "construction contract"],
            terms_ar=["\u0627\u0633\u062a\u0635\u0646\u0627\u0639"],
        ),
        RouterSeedRecord(
            route_id="ijarah-accounting",
            canonical_concept="ijarah",
            contract_family=ContractFamily.IJARAH,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-32"],
            terms_en=["ijarah", "ijara", "lease"],
            terms_ar=["\u0625\u062c\u0627\u0631\u0629", "\u0627\u0644\u0625\u062c\u0627\u0631\u0629"],
        ),
        RouterSeedRecord(
            route_id="mudaraba-accounting",
            canonical_concept="mudaraba",
            contract_family=ContractFamily.MUDARABA,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-3"],
            terms_en=["mudaraba", "mudarabah"],
            terms_ar=["\u0645\u0636\u0627\u0631\u0628\u0629"],
        ),
        RouterSeedRecord(
            route_id="musharaka-accounting",
            canonical_concept="musharaka",
            contract_family=ContractFamily.MUSHARAKA,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-4"],
            terms_en=["musharaka", "musharakah", "partnership"],
            terms_ar=["\u0645\u0634\u0627\u0631\u0643\u0629"],
        ),
        RouterSeedRecord(
            route_id="wakala-investment-accounting",
            canonical_concept="wakala bi al-istithmar",
            contract_family=ContractFamily.WAKALA,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-31"],
            terms_en=["wakala", "wakalah", "investment agency", "wakala bi al-istithmar"],
            terms_ar=["\u0648\u0643\u0627\u0644\u0629", "\u0648\u0643\u0627\u0644\u0629 \u0628\u0627\u0644\u0627\u0633\u062a\u062b\u0645\u0627\u0631"],
        ),
        RouterSeedRecord(
            route_id="zakah-accounting",
            canonical_concept="zakah",
            contract_family=ContractFamily.UNKNOWN,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-9", "FAS-39"],
            terms_en=["zakah", "zakat"],
            terms_ar=[zakah_ar],
            ambiguity_warning="Accounting/calculation support only; obligation questions need proper source routing.",
        ),
        RouterSeedRecord(
            route_id="takaful-accounting",
            canonical_concept="takaful",
            contract_family=ContractFamily.UNKNOWN,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-12", "FAS-13", "FAS-15"],
            terms_en=["takaful", "islamic insurance"],
            terms_ar=[takaful_ar],
        ),
        RouterSeedRecord(
            route_id="sukuk-shares-accounting",
            canonical_concept="sukuk and shares",
            contract_family=ContractFamily.SUKUK,
            question_types=[QuestionType.ACCOUNTING, QuestionType.EXPLANATION],
            source_families=[SourceFamily.FAS],
            candidate_standards=["FAS-33", "FAS-34"],
            terms_en=["sukuk", "shares", "similar instruments"],
            terms_ar=[sukuk_ar, shares_ar],
        ),
    ]
    seeds.extend(extra_records)
    return RouterSeedRegistry(seeds)
