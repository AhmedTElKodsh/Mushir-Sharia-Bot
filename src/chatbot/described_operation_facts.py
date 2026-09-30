"""Conservative text extraction and append-only reconciliation of personal facts.

Only explicit supported forms are extracted. Unrecognized wording stays unknown;
provider names and the word instalment never establish a contract mechanism.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import re

from src.models.evidence import (
    FACT_SLOTS, EvidenceScope, FactCandidate, FactObservation, FactSnapshot, FactResolution,
    Money, UserTurnProvenance,
)

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "01234567890123456789,.")
_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\w%]|[,.]\d)"
_MONEY = rf"(?:EGP\s*)?(?P<amount>{_NUMBER})(?:\s*(?:EGP|جنيه(?:ات)?))?"
_NEGATION = r"\b(?:not|no|or|either)\b|(?<!\w)(?:ليس|مش|بدون|او|أو)(?!\w)"
MAX_INSTALMENTS = 1000


def _plausible_count(digits: str) -> bool:
    return len(digits) <= 4 and 0 < int(digits) <= MAX_INSTALMENTS


def parse_schedule_reply(text: str, slot: str):
    """Parse a direct answer to a specific schedule-field question, no inference."""
    normalized = text.translate(_DIGITS).strip()
    if slot in {"cash_price", "financed_or_final_price", "down_payment", "instalment_amount"}:
        match = re.fullmatch(rf"{_MONEY}[.!]?", normalized, re.I)
        if match and re.search(r"\bEGP\b|جنيه", normalized, re.I):
            return Money(amount=Decimal(match["amount"].replace(",", "")), currency="EGP")
    if slot == "instalment_count" and re.fullmatch(r"[0-9]{1,4}", normalized) and _plausible_count(normalized):
        return int(normalized)
    return None


def parse_confirmed_schedule_reply(text: str, slot: str):
    """Bind a complete, unqualified schedule confirmation to one pending field.

    A marker in an earlier clause must never endorse a different later claim.
    Unrecognized qualifications remain unresolved rather than being stripped.
    """
    labels = {
        "financed_or_final_price": r"(?:the )?(?:total payable|final price)|السعر النهائي|الإجمالي المستحق",
        "down_payment": r"(?:the )?(?:deposit|down payment)|المقدم|مقدم",
        "cash_price": r"(?:the )?cash price|السعر النقدي|سعر الكاش",
        "instalment_amount": r"(?:the )?instal+ment amount|قيمة القسط",
        "instalment_count": r"(?:the )?(?:number of instal+ments|instal+ment count)|عدد الأقساط",
    }
    if slot not in labels:
        return None
    marker = r"(?:according to my (?:repayment )?schedule|my (?:repayment )?schedule says|حسب جدول السداد|وفقا لجدول السداد)"
    match = re.fullmatch(rf"\s*{marker}[\s,:،]+(?:{labels[slot]})\s*(?:is\s+|[:=]\s*)?(?P<reply>.+?)\s*", text, re.I)
    return parse_schedule_reply(match["reply"], slot) if match else None


def extract_operation_facts(text: str, *, session_id: str, transaction_id: str,
                            turn_id: str, version: int, recorded_at: datetime) -> FactSnapshot:
    scope = EvidenceScope(lane="personal", transaction_id=transaction_id, document_scope="schedule")
    source = UserTurnProvenance(session_id=session_id, turn_id=turn_id, exact_text=text,
                               recorded_at=recorded_at, version=version, scope=scope)
    normalized = text.translate(_DIGITS)
    values: dict[str, list] = {}

    def add(slot, value):
        options = values.setdefault(slot, [])
        if not any(type(item) is type(value) and item == value for item in options):
            options.append(value)

    def matches(pattern):
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            # Do not turn negated or alternative clauses into asserted facts.
            prefix = re.split(r"[.!?؟;\n،]|(?<!\d),(?!\d)|\bbut\b", normalized[:match.start()])[-1]
            suffix = normalized[match.end():]
            if re.match(r"\s+(?:\d|million\b|thousand\b|[km]\b|ألف|الف|مليون)", suffix, re.I):
                continue
            if (re.search(_NEGATION, prefix, re.I)
                    or re.match(r"\s*(?:or\b|او\b|أو\b)", suffix, re.I)):
                continue
            yield match

    if re.search(r"iphone|آيفون|ايفون|أيفون", normalized, re.I):
        add("asset", "iPhone")
    has_egp = bool(re.search(r"\bEGP\b|جنيه", normalized, re.I))
    foreign = r"\b(?:USD|EUR|SAR|AED|GBP)\b|[$€£]|دولار|ريال|درهم|يورو"

    def foreign_nearby(match):
        return bool(re.search(foreign, normalized[max(0, match.start() - 12):match.end() + 12], re.I))

    if has_egp:
        patterns = {
            "down_payment": rf"(?:\bdeposit|\bdown payment|ب?مقدم)\s*(?:of\s+|is\s+|[:=]\s*)?{_MONEY}",
            "cash_price": rf"(?:\bcash price|السعر النقدي|سعر الكاش)\s*(?:is\s+|[:=]\s*)?{_MONEY}",
            "financed_or_final_price": rf"(?:\btotal payable|\bfinal price|اجمالي المبلغ|إجمالي المبلغ|السعر النهائي)\s*(?:is\s+|[:=]\s*)?{_MONEY}",
        }
        for slot, pattern in patterns.items():
            for match in matches(pattern):
                if re.search(r"\bEGP\b|جنيه", match[0], re.I) and not foreign_nearby(match):
                    add(slot, Money(amount=Decimal(match["amount"].replace(",", "")), currency="EGP"))
        for match in matches(rf"(?<![\d.,-]){_MONEY}\s+(?:down\b|مقدم)"):
            if re.search(r"\bEGP\b|جنيه", match[0], re.I) and not foreign_nearby(match):
                add("down_payment", Money(amount=Decimal(match["amount"].replace(",", "")), currency="EGP"))

    schedule = rf"(?<![\d.,-])(?P<count>\d+)(?![\d.,])\s*(?:[x×]|instalments?\s+(?:of|at)|installments?\s+(?:of|at)|قسط\s*(?:كل قسط|بقيمة))\s*{_MONEY}"
    monthly = rf"(?<![\d.,-]){_MONEY}\s+(?:monthly for|شهريا لمدة)\s*(?P<count>\d+)(?![\d.,])\s*(?:months?\b|شهر)"
    for pattern in (schedule, monthly):
        for match in matches(pattern):
            if _plausible_count(match["count"]):
                add("instalment_count", int(match["count"]))
                if re.search(r"\bEGP\b|جنيه", match[0], re.I) and not foreign_nearby(match):
                    add("instalment_amount", Money(amount=Decimal(match["amount"].replace(",", "")), currency="EGP"))

    # This identifies only the named party, not its regulatory role or mechanism.
    for match in matches(r"(?:\bfinancing party is|\bfinanced by|جهة التمويل هي|التمويل من)\s+([^.!?؟\n,،;]+)"):
        party = re.split(r"\s+(?:and|with|but|then|which|paid)\s+|\s+و(?=\w)", match[1].strip(), maxsplit=1)[0].strip()
        if party and not re.search(r"\d", party) and not re.search(
                r"\b(?:unknown|not|unsure|either|or)\b|معرفش|لا أعرف|مش عارف|(?<!\w)(?:او|أو)(?!\w)", party, re.I):
            add("financing_party", party)

    facts = []
    for slot in FACT_SLOTS:
        common = dict(slot=slot, scope=scope, version=version, recorded_at=recorded_at)
        candidates = values.get(slot, [])
        if not candidates:
            facts.append(FactObservation(**common, status="unknown", unobserved_reason="in_customer_schedule"))
        elif len(candidates) == 1:
            facts.append(FactObservation(**common, status="user_reported", value=candidates[0], source=source))
        else:
            facts.append(FactObservation(**common, status="conflicting", candidates=tuple(
                FactCandidate(status="user_reported", value=value, source=source) for value in candidates)))
    return FactSnapshot(snapshot_id=f"{transaction_id}:{version}", version=version,
                        recorded_at=recorded_at, facts=tuple(facts))


def reconcile_operation_facts(previous: FactSnapshot, incoming: FactSnapshot) -> FactSnapshot:
    """Keep earlier knowledge; contradictory assertions require reconciliation.

    An ordinary follow-up, including the word 'correction', cannot silently erase
    an earlier assertion. Explicit resolution is a separate reviewed operation.
    """
    previous = FactSnapshot.model_validate(previous)
    incoming = FactSnapshot.model_validate(incoming)
    if incoming.version != previous.version + 1 or incoming.recorded_at < previous.recorded_at:
        raise ValueError("reconciliation requires the next chronological snapshot revision")
    scopes = {fact.scope.model_dump_json() for fact in (*previous.facts, *incoming.facts)}
    sessions = set()
    for fact in (*previous.facts, *incoming.facts):
        sources = [fact.source] + [candidate.source for candidate in fact.candidates]
        for source in sources:
            if isinstance(source, UserTurnProvenance):
                sessions.add(source.session_id)
    if len(scopes) != 1 or len(sessions) > 1:
        raise ValueError("reconciliation cannot cross transaction scope or user session")
    merged = {fact.slot: fact for fact in previous.facts}
    for new in incoming.facts:
        old = merged.get(new.slot)
        if old is None or old.status == "unknown":
            merged[new.slot] = new
            continue
        if new.status == "unknown":
            continue
        def candidates(fact):
            return fact.candidates if fact.status == "conflicting" else (
                FactCandidate(value=fact.value, status=fact.status, source=fact.source),)
        options = list(candidates(old))
        for candidate in candidates(new):
            if not any(type(item.value) is type(candidate.value) and item.value == candidate.value for item in options):
                options.append(candidate)
        if len(options) > 1:
            merged[new.slot] = FactObservation(slot=new.slot, scope=new.scope, version=incoming.version,
                                               recorded_at=incoming.recorded_at, status="conflicting", candidates=tuple(options))
    return incoming.model_copy(update={"facts": tuple(merged.values())})


def resolve_operation_fact(previous: FactSnapshot, incoming: FactSnapshot, *, slot: str):
    """Explicitly select a new assertion while retaining the prior conflict.

    The conversation adapter must establish a confirmation of the requested
    schedule field. This operation grants no authority over observed documents.
    """
    reconciled = reconcile_operation_facts(previous, incoming)
    old = next((fact for fact in previous.facts if fact.slot == slot), None)
    selected = next((fact for fact in incoming.facts if fact.slot == slot), None)
    if old is None or selected is None:
        raise ValueError("resolution requires an existing slot and an incoming assertion")
    resolution = FactResolution(previous_fact=old, selected_fact=selected)
    return reconciled.model_copy(update={"facts": tuple(
        selected if fact.slot == slot else fact for fact in reconciled.facts)}), resolution
