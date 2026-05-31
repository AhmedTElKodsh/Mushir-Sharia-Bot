"""
Standard Resolver — Pre-Retrieval Standard Filter
==================================================
Maps a (concept, ContractFamily) pair to a list of specific AAOIFI standard
numbers that MUST be searched, filtering vector retrieval BEFORE the embedding
query is issued.

This eliminates the probabilistic retrieval problem identified in the
party-mode rethink (2026-05-28): without this resolver, a query about
"غرامة التأخير في عقود المقاولات" could retrieve from any standard
mentioning penalties, including SS-19 (Riba) — producing a false fatwa.

With this resolver:
  resolve("late_penalty", ContractFamily.MUQAWALA) → ["SS-11", "SS-05"]
  resolve("late_payment_penalty", ContractFamily.GENERAL_SHARIA) → ["SS-19"]

The retriever uses these standard IDs to filter chunk metadata BEFORE the
dense search: chunk["standard_id"] must be in resolve(concept, family).

References:
  - AAOIFI SS-05  Guarantees (الضمانات)
  - AAOIFI SS-07  Salam (السلم)
  - AAOIFI SS-09  Ijarah (الإجارة)
  - AAOIFI SS-10  Salam and Parallel Salam
  - AAOIFI SS-11  Istisna' and Parallel Istisna'
  - AAOIFI SS-12  Musharaka (المشاركة)
  - AAOIFI SS-13  Mudaraba (المضاربة)
  - AAOIFI SS-17  Investment Sukuk (صكوك الاستثمار)
  - AAOIFI SS-19  Qard (القرض)
  - AAOIFI SS-23  Wakalah (الوكالة)
  - AAOIFI SS-28  Murabaha (المرابحة)
  - AAOIFI SS-30  Tawarruq (التورق)
  - AAOIFI SS-35  Wakala in Investment (وكالة في الاستثمار)
"""

from __future__ import annotations

from src.chatbot.contract_family_router import ContractFamily

# ---------------------------------------------------------------------------
# The core mapping: (concept_id, contract_family) → [AAOIFI standard IDs]
#
# Concept IDs match the `concept_id` field in ConceptOntology YAML files.
# Standard IDs use the "SS-XX" and "FAS-XX" conventions from the source catalog.
#
# When a (concept, family) pair is not present, resolve() returns [].
# Callers should fall back to unrestricted retrieval in that case.
# ---------------------------------------------------------------------------

CONTEXT_TO_STANDARD_MAP: dict[tuple[str, str], list[str]] = {

    # ── Late payment / delay penalty ───────────────────────────────────────
    # Construction/Istisna context: route to SS-11 + SS-05. SS-10 is Salam.
    ("late_penalty",         ContractFamily.MUQAWALA):      ["SS-05", "SS-11"],
    ("late_payment_penalty", ContractFamily.MUQAWALA):      ["SS-05", "SS-11"],
    # Murabaha deferred payment context: disputed — possible charity clause
    ("late_payment_penalty", ContractFamily.MURABAHA):      ["SS-28", "SS-19"],
    # General debt context: prohibited Riba
    ("late_payment_penalty", ContractFamily.GENERAL_SHARIA): ["SS-19"],

    # ── Ownership / title transfer ─────────────────────────────────────────
    ("ownership_transfer",   ContractFamily.IJARA):         ["SS-09"],
    ("ownership_transfer",   ContractFamily.MUSHARAKA):     ["SS-12"],
    ("ownership_transfer",   ContractFamily.MURABAHA):      ["SS-28"],

    # ── Guarantee / capital protection ────────────────────────────────────
    # Mudaraba: guaranteeing capital converts to Qard → prohibited
    ("capital_guarantee",    ContractFamily.MUDHARABA):     ["SS-13"],
    ("capital_guarantee",    ContractFamily.MUSHARAKA):     ["SS-12"],
    # Sukuk: issuer guarantee prohibited; third-party permissible
    ("capital_guarantee",    ContractFamily.GENERAL_SHARIA): ["SS-17"],
    # Performance bond in construction — permissible via Kafala
    ("performance_bond",     ContractFamily.MUQAWALA):      ["SS-05", "SS-11"],
    ("performance_bond",     ContractFamily.KAFALA):        ["SS-05"],

    # ── Return / profit guarantee ──────────────────────────────────────────
    # Wakala: guaranteeing return converts agency to Qard
    ("return_guarantee",     ContractFamily.WAKALA):        ["SS-35", "SS-23"],
    # Mudaraba: same — capital guarantee violates mudaraba structure
    ("return_guarantee",     ContractFamily.MUDHARABA):     ["SS-13"],

    # ── Profit / markup ────────────────────────────────────────────────────
    ("profit_distribution",  ContractFamily.MUDHARABA):     ["SS-13"],
    ("profit_distribution",  ContractFamily.MUSHARAKA):     ["SS-12"],
    ("markup_increase",      ContractFamily.MURABAHA):      ["SS-28"],
    # Fixed periodic distribution on Sukuk: may convert to Riba bond
    ("fixed_distribution",   ContractFamily.GENERAL_SHARIA): ["SS-17"],

    # ── Salary / fee to managing party ────────────────────────────────────
    # Mudarib salary: prohibited — converts Mudaraba to Ijarah
    ("salary_to_mudarib",    ContractFamily.MUDHARABA):     ["SS-13"],
    # Wakala management fee: permissible as separate fee contract
    ("management_fee",       ContractFamily.WAKALA):        ["SS-23", "SS-35"],

    # ── Tawarruq ───────────────────────────────────────────────────────────
    # Organised Tawarruq: prohibited (SS-30); unorganised: disputed
    ("tawarruq_organised",   ContractFamily.MURABAHA):      ["SS-30"],
    ("tawarruq_unorganised", ContractFamily.MURABAHA):      ["SS-28", "SS-30"],

    # ── Parallel Istisna ───────────────────────────────────────────────────
    ("parallel_istisna",     ContractFamily.MUQAWALA):      ["SS-11"],
    ("subcontract_validity", ContractFamily.MUQAWALA):      ["SS-11"],

    # ── Delivery / Salam ───────────────────────────────────────────────────
    ("salam_delivery",       ContractFamily.GENERAL_SHARIA): ["SS-07"],

    # ── Maintenance obligations ────────────────────────────────────────────
    # Ijarah: structural = lessor; operational = lessee (both in SS-09)
    ("maintenance_duty",     ContractFamily.IJARA):         ["SS-09"],

    # ── Currency / FX ─────────────────────────────────────────────────────
    # Forward contracts: generally not permissible — spot settlement required
    ("currency_forward",     ContractFamily.GENERAL_SHARIA): ["SS-01"],

    # ── Qard Hassan conditions ─────────────────────────────────────────────
    # Any benefit conditioned on Qard = Riba
    ("conditional_benefit",  ContractFamily.GENERAL_SHARIA): ["SS-19"],

    # ── Buyback / Bay' al-Wafa ─────────────────────────────────────────────
    ("buyback_condition",    ContractFamily.MURABAHA):      ["SS-28", "SS-19"],
    ("buyback_condition",    ContractFamily.GENERAL_SHARIA): ["SS-28", "SS-19"],

    # ── Rent in Diminishing Musharaka ──────────────────────────────────────
    ("rent_increase",        ContractFamily.MUSHARAKA):     ["SS-12"],

    # ── Kafala fee ─────────────────────────────────────────────────────────
    # Guarantor charging a fee: prohibited (converts to Riba) per majority view
    ("guarantee_fee",        ContractFamily.KAFALA):        ["SS-05"],

    # ── Ijara residual value ───────────────────────────────────────────────
    ("residual_value_guarantee", ContractFamily.IJARA):     ["SS-09"],

    # ── Murabaha rollover / refinancing ────────────────────────────────────
    ("loan_rollover",        ContractFamily.MURABAHA):      ["SS-28", "SS-19"],
}


def resolve(concept: str, family: ContractFamily) -> list[str]:
    """
    Return the list of AAOIFI standard IDs that must be searched for the
    given (concept, contract_family) combination.

    Args:
        concept: Concept ID from ConceptOntology (e.g. "late_payment_penalty").
        family: Resolved ContractFamily from ContractFamilyRouter.

    Returns:
        List of standard IDs (e.g. ["SS-10", "SS-05"]).
        Empty list if no mapping exists — caller should fall back to
        unrestricted retrieval.
    """
    return CONTEXT_TO_STANDARD_MAP.get((concept, family), [])


def resolve_bulk(concepts: list[str], family: ContractFamily) -> list[str]:
    """
    Resolve multiple concepts for the same family and return a deduplicated,
    order-preserving list of AAOIFI standard IDs.

    Args:
        concepts: List of concept IDs extracted from the query.
        family: Resolved ContractFamily from ContractFamilyRouter.

    Returns:
        Deduplicated list of standard IDs across all concepts.
    """
    seen: dict[str, None] = {}
    for concept in concepts:
        for standard in resolve(concept, family):
            seen[standard] = None
    return list(seen)


def all_standards_for_family(family: ContractFamily) -> list[str]:
    """
    Return all unique AAOIFI standard IDs associated with a contract family,
    regardless of concept. Used as a fallback filter when concept extraction
    fails but contract family is known with high confidence.

    Args:
        family: Resolved ContractFamily.

    Returns:
        Deduplicated list of standard IDs for this family.
    """
    seen: dict[str, None] = {}
    for (_, fam), standards in CONTEXT_TO_STANDARD_MAP.items():
        if fam == family:
            for std in standards:
                seen[std] = None
    return list(seen)
