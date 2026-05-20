"""Governed financial concept map for bilingual query understanding."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from src.models.commercial import ContractFamily, SourceFamily
from src.rag.query_preprocessor import QueryPreprocessor


@dataclass(frozen=True)
class ConceptEntry:
    concept_id: str
    contract_family: ContractFamily
    labels_en: List[str]
    labels_ar: List[str] = field(default_factory=list)
    transliterations: List[str] = field(default_factory=list)
    colloquial_ar: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    candidate_source_families: List[SourceFamily] = field(default_factory=list)
    required_facts: List[str] = field(default_factory=list)
    ambiguity_warnings: List[str] = field(default_factory=list)
    expected_standards: List[str] = field(default_factory=list)

    def terms(self) -> Set[str]:
        values = (
            self.labels_en
            + self.labels_ar
            + self.transliterations
            + self.colloquial_ar
            + self.synonyms
        )
        return {term.strip().lower() for term in values if term.strip()}


class ConceptMap:
    """Lookup layer around governed concept entries."""

    def __init__(self, entries: Iterable[ConceptEntry]) -> None:
        self._entries = {entry.concept_id: entry for entry in entries}
        self._term_index: Dict[str, str] = {}
        for entry in self._entries.values():
            for term in entry.terms():
                self._term_index[QueryPreprocessor.normalize(term).lower()] = entry.concept_id

    def get(self, concept_id: str) -> ConceptEntry:
        return self._entries[concept_id]

    def match(self, query: str) -> List[ConceptEntry]:
        normalized = QueryPreprocessor.normalize(query).lower()
        expanded = QueryPreprocessor.expand_terms(query)
        candidates: List[ConceptEntry] = []
        seen: Set[str] = set()
        for term, concept_id in self._term_index.items():
            if term in normalized or term in expanded:
                if concept_id not in seen:
                    candidates.append(self._entries[concept_id])
                    seen.add(concept_id)
        return candidates

    def primary_match(self, query: str) -> Optional[ConceptEntry]:
        matches = self.match(query)
        return matches[0] if matches else None

    def source_families_for(self, query: str) -> Set[SourceFamily]:
        families: Set[SourceFamily] = set()
        for entry in self.match(query):
            families.update(entry.candidate_source_families)
        return families


def default_concept_map() -> ConceptMap:
    """Return the first governed concept set from the 2026-05-19 plan."""
    murabaha_ar = "\u0645\u0631\u0627\u0628\u062d\u0629"
    al_murabaha_ar = "\u0627\u0644\u0645\u0631\u0627\u0628\u062d\u0629"
    ijarah_ar = "\u0625\u062c\u0627\u0631\u0629"
    al_ijarah_ar = "\u0627\u0644\u0625\u062c\u0627\u0631\u0629"
    taqseet_ar = "\u062a\u0642\u0633\u064a\u0637"
    installment_sale_ar = "\u0628\u064a\u0639 \u062a\u0642\u0633\u064a\u0637"
    with_installments_ar = "\u0628\u0627\u0644\u062a\u0642\u0633\u064a\u0637"
    late_penalty_ar = "\u063a\u0631\u0627\u0645\u0629 \u062a\u0623\u062e\u064a\u0631"
    delay_ar = "\u062a\u0623\u062e\u064a\u0631"
    delay_plain_ar = "\u062a\u0627\u062e\u064a\u0631"
    riba_ar = "\u0631\u0628\u0627"
    interest_ar = "\u0641\u0648\u0627\u0626\u062f"

    return ConceptMap(
        [
            ConceptEntry(
                concept_id="murabaha",
                contract_family=ContractFamily.MURABAHA,
                labels_en=["murabaha", "murabahah", "cost-plus sale", "deferred payment sale"],
                labels_ar=[murabaha_ar, al_murabaha_ar],
                transliterations=["murabaha", "murabahah", "morabaha"],
                colloquial_ar=[
                    installment_sale_ar,
                    with_installments_ar,
                    "\u0627\u0642\u0633\u0627\u0637",
                    taqseet_ar,
                ],
                synonyms=["installment sale", "instalment sale", "buy now pay later", "bnpl"],
                candidate_source_families=[SourceFamily.FAS, SourceFamily.SHARIA_STANDARD],
                required_facts=[
                    "asset",
                    "price_or_markup",
                    "ownership_sequence",
                    "possession_or_risk_bearing",
                ],
                ambiguity_warnings=[
                    "Installment wording can describe murabaha, a conventional loan, or another deferred sale."
                ],
                expected_standards=["FAS-28", "SS-08"],
            ),
            ConceptEntry(
                concept_id="ijarah",
                contract_family=ContractFamily.IJARAH,
                labels_en=["ijarah", "ijara", "lease"],
                labels_ar=[ijarah_ar, al_ijarah_ar],
                transliterations=["ijarah", "ijara"],
                synonyms=["usufruct", "lease to own"],
                candidate_source_families=[SourceFamily.FAS, SourceFamily.SHARIA_STANDARD],
                required_facts=["asset", "usufruct", "lease_term", "maintenance_responsibility"],
                ambiguity_warnings=["Lease wording can mix accounting treatment with permissibility questions."],
                expected_standards=["FAS-32"],
            ),
            ConceptEntry(
                concept_id="late_payment_penalty",
                contract_family=ContractFamily.UNKNOWN,
                labels_en=["late payment penalty", "late fee", "default charge"],
                labels_ar=[late_penalty_ar, delay_plain_ar, delay_ar],
                transliterations=["taakhir", "ta2kheer"],
                synonyms=["penalty", "collection cost", "default fee", "charity clause"],
                candidate_source_families=[SourceFamily.SHARIA_STANDARD, SourceFamily.FAS],
                required_facts=["penalty_beneficiary", "actual_collection_cost", "contract_family"],
                ambiguity_warnings=["Late-payment clauses need Shariah-source evidence and beneficiary facts."],
            ),
            ConceptEntry(
                concept_id="riba",
                contract_family=ContractFamily.QARD,
                labels_en=["riba", "interest"],
                labels_ar=[riba_ar, interest_ar],
                transliterations=["ribah"],
                synonyms=["usury", "extra repayment"],
                candidate_source_families=[SourceFamily.SHARIA_STANDARD],
                required_facts=["loan_structure", "increment_basis"],
                ambiguity_warnings=["Riba questions are fatwa-adjacent and must fail closed without Shariah evidence."],
            ),
        ]
    )
