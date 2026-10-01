"""Personal-operation conversation adapter over typed evidence and approved rules."""
from __future__ import annotations

from datetime import UTC, datetime
import re
from uuid import uuid4

from pydantic import Field, StrictInt, model_validator

from src.chatbot.described_operation_facts import (
    extract_operation_facts, reconcile_operation_facts, resolve_operation_fact,
    parse_schedule_reply, parse_confirmed_schedule_reply, known_currency,
)
from src.models.evidence import (
    AnswerDecision, DecisionReviewRow, EvidenceModel, FactSnapshot, FactResolution, GateDecision,
    Money, Text, UserTurnProvenance,
)
from src.models.ruling import AnswerContract, ComplianceStatus
from src.ontology.approved_card_evaluator import ApprovedCardEvaluator


class OperationConversation(EvidenceModel):
    session_id: Text
    transaction_id: Text
    snapshot: FactSnapshot
    clarification_count: StrictInt = Field(default=0, ge=0)
    pending_slot: Text | None = None
    resolutions: tuple[FactResolution, ...] = ()

    @model_validator(mode="after")
    def owned_snapshot(self):
        for fact in self.snapshot.facts:
            if fact.scope.lane != "personal" or fact.scope.transaction_id != self.transaction_id:
                raise ValueError("conversation snapshot must belong to its transaction")
            for source in [fact.source, *(candidate.source for candidate in fact.candidates)]:
                if isinstance(source, UserTurnProvenance) and source.session_id != self.session_id:
                    raise ValueError("conversation cannot contain another session's facts")
        for resolution in self.resolutions:
            selected = resolution.selected_fact
            if selected.scope.transaction_id != self.transaction_id or selected.source.session_id != self.session_id:
                raise ValueError("resolution history must belong to this conversation")
        return self


class DescribedOperationService:
    MAX_CLARIFICATIONS = 2

    def __init__(self, cards=()):
        self.evaluator = ApprovedCardEvaluator(cards)

    @staticmethod
    def accepts(text: str, previous: OperationConversation | None = None) -> bool:
        if re.search(r"\b(?:do not|don't) (?:have|want) (?:any |a |an )?(?:instal+ments?|transaction|purchase|payment plan)\b|مش عندي (?:تقسيط|معاملة)", text, re.I):
            return False
        personal = re.search(r"\b(?:I|my|we|our)\b|اشتريت|اشتري|عايز|عاوز|دفعت|هدفع", text, re.I)
        terms = re.search(r"instal+ments?|monthly|deposit|down payment|\d\s*[x×]|قسط|تقسيط|مقدم|شهريا", text, re.I)
        if personal and terms:
            return True
        if previous is None:
            return False
        # Explicit fact updates and short answers to a pending question can
        # continue a transaction. A new question is routed independently.
        if re.search(r"[?؟]", text) or re.match(r"\s*(?:what|why|how|define|explain|ما هو|ما هي|اشرح)\b", text, re.I):
            return False
        return bool(DescribedOperationService._answers_pending(
            text, previous.pending_slot, known_currency(previous.snapshot)) or re.search(
            r"total payable|final price|cash price|deposit|financed by|financing party|مقدم|السعر النهائي|التمويل من", text, re.I))

    @classmethod
    def _answers_pending(cls, text: str, slot: str | None, currency: str | None = None) -> bool:
        """A reply must look like an answer to the open question, not just be short."""
        if not slot or len(text) > 160:
            return False
        if re.fullmatch(r"\s*(?:please\s+)?continue[.!]?\s*|\s*(?:تابع|اكمل)[.!]?\s*", text, re.I):
            return True  # Unanswered filler still consumes the clarification budget.
        if slot == "financing_party":
            return bool(cls._financier_reply(text) or cls._does_not_know(text))
        if slot not in {"cash_price", "financed_or_final_price", "down_payment", "instalment_amount",
                        "instalment_count", "payment_breakdown"}:
            return True  # A rule-defined slot has no fixed grammar; length and the no-question check bound it.
        if slot == "payment_breakdown":
            return bool(re.search(r"\d|fees?|charges?|insurance|admin|interest|رسوم|مصاريف|تأمين|فوائد|ضريبة", text, re.I)
                        or cls._does_not_know(text))
        return (parse_schedule_reply(text, slot, currency) is not None
                or parse_confirmed_schedule_reply(text, slot) is not None or cls._does_not_know(text))

    def answer(self, text: str, *, session_id: str, request_id: str,
               previous: OperationConversation | None, language: str):
        if previous is not None:
            previous = OperationConversation.model_validate(previous)
            if previous.session_id != session_id:
                raise ValueError("operation state belongs to another session")
        if self._starts_new_transaction(text):
            previous = None
        now = datetime.now(UTC)
        transaction_id = previous.transaction_id if previous else str(uuid4())
        version = previous.snapshot.version + 1 if previous else 1
        turn_id = str(uuid4())
        incoming = extract_operation_facts(text, session_id=session_id, transaction_id=transaction_id,
                                           turn_id=turn_id, version=version, recorded_at=now)
        direct_schedule_reply = False
        if previous and previous.pending_slot:
            old = next((fact for fact in previous.snapshot.facts if fact.slot == previous.pending_slot), None)
            if old and old.status == "conflicting":
                value = parse_schedule_reply(text, previous.pending_slot, known_currency(previous.snapshot))
                if value is None:
                    value = parse_confirmed_schedule_reply(text, previous.pending_slot)
                if value is not None:
                    source = UserTurnProvenance(session_id=session_id, turn_id=turn_id, exact_text=text,
                                               recorded_at=now, version=version, scope=old.scope)
                    incoming = incoming.model_copy(update={"facts": tuple(
                        fact.model_copy(update={"status": "user_reported", "value": value, "source": source,
                                                "unobserved_reason": None}) if fact.slot == old.slot else fact
                        for fact in incoming.facts)})
                    direct_schedule_reply = True
        if previous and previous.pending_slot == "financing_party":
            party = self._financier_reply(text)
            if party:
                items = list(incoming.facts)
                index = next(i for i, item in enumerate(items) if item.slot == "financing_party")
                if items[index].status == "unknown":
                    source = UserTurnProvenance(session_id=session_id, turn_id=turn_id, exact_text=text,
                                               recorded_at=now, version=version, scope=items[index].scope)
                    items[index] = items[index].model_copy(update={"status": "user_reported", "value": party,
                                                                "source": source, "unobserved_reason": None})
                    incoming = incoming.model_copy(update={"facts": tuple(items)})
        snapshot = reconcile_operation_facts(previous.snapshot, incoming) if previous else incoming
        resolutions = ()
        if previous and previous.pending_slot and direct_schedule_reply:
            old = next((fact for fact in previous.snapshot.facts if fact.slot == previous.pending_slot), None)
            selected = next((fact for fact in incoming.facts if fact.slot == previous.pending_slot), None)
            if (old and old.status == "conflicting" and selected and selected.status == "user_reported"
                    and all(isinstance(candidate.source, UserTurnProvenance) for candidate in old.candidates)):
                snapshot, resolution = resolve_operation_fact(previous.snapshot, incoming, slot=previous.pending_slot)
                resolutions = (resolution,)
        facts = {fact.slot: fact for fact in snapshot.facts}
        scope = next(iter(facts.values())).scope
        count = previous.clarification_count if previous else 0
        exhausted = count >= self.MAX_CLARIFICATIONS
        evaluation = self.evaluator.evaluate(snapshot, scope=scope, session_id=session_id,
                                              expected_snapshot_version=version, clarification_exhausted=exhausted)
        pending = None
        question = None
        conflicts = [fact.slot for fact in snapshot.facts if fact.status == "conflicting"]
        payment_check = self._payment_check(facts)
        if conflicts:
            reason = "conflicting_user_facts"
            pending = conflicts[0]
            if not exhausted:
                labels = {"financed_or_final_price": "الإجمالي المستحق", "down_payment": "المقدم",
                          "cash_price": "السعر النقدي", "instalment_count": "عدد الأقساط", "instalment_amount": "قيمة القسط",
                          "financing_party": "جهة التمويل"}
                english_labels = {"financed_or_final_price": "total payable", "down_payment": "deposit",
                                  "cash_price": "cash price", "instalment_count": "number of instalments",
                                  "instalment_amount": "instalment amount", "financing_party": "financing party"}
                question = (f"ما قيمة {labels.get(pending, 'البند المختلف')} المذكورة في جدول السداد؟" if language == "ar"
                            else f"What {english_labels.get(pending, 'value for the disputed item')} does your repayment schedule state?")
        elif facts["financing_party"].status == "unknown":
            reason = "financing_party_unknown"
            pending = "financing_party"
            if not exhausted and not self._does_not_know(text):
                question = ("مين مقدم خطة التقسيط: المحل نفسه ولا بنك أو شركة تمويل؟" if language == "ar"
                            else "Who provides the instalment plan—the store itself, or a bank or finance company?")
        elif payment_check:
            reason = "payment_total_discrepancy"
            if not exhausted:
                pending = "payment_breakdown"
                question = ("ما تفصيل الرسوم والمبالغ في جدول السداد الذي يوضح الفرق بين الإجمالي والمقدم مع الأقساط؟" if language == "ar" else
                            "What fees or payment details in the repayment schedule explain the difference between the stated total and the deposit plus instalments?")
        else:
            reason = evaluation.reason
            if evaluation.status == "evaluated":
                # A rule-scoped result is not an overall ruling: rendering it and the
                # remaining overall gates are unfinished, so the answer stays withheld.
                reason = "approved_rule_evaluated_overall_gates_pending"
            if evaluation.status == "clarification_needed" and evaluation.question:
                pending = evaluation.question_slot
                question = evaluation.question
        rule_evaluated = evaluation.status == "evaluated" and reason == "approved_rule_evaluated_overall_gates_pending"
        if not question:
            pending = None  # Nothing is being asked, so no later message can answer it.
        gates = (
            GateDecision(gate="intent_and_scope", status="passed", reason="personal_transaction_scope"),
            GateDecision(gate="typed_extraction", status="passed", reason="explicit_user_assertions_only"),
            GateDecision(gate="material_fact", status="passed" if rule_evaluated else "blocked",
                         reason="approved_rule_material_facts_complete" if rule_evaluated else reason),
            GateDecision(gate="selective_answer", status="blocked", reason="no_overall_judgment_authorized"),
        )
        if question:
            decision = AnswerDecision(decision="CLARIFICATION_NEEDED", reason=reason, questions=(question,), gates=gates)
            answer_text = question
            count += 1
        else:
            needed = ("agreement or repayment disclosure identifying the financier and complete payment terms",
                      "scholar-approved rule mapping to the verified contract mechanism")
            if rule_evaluated:
                needed = ("scholar review of the rule-scoped result and the remaining overall-conclusion gates",)
            decision = AnswerDecision(decision="INSUFFICIENT_DATA", reason=reason,
                                      needed_documents_or_reviews=needed, gates=gates)
            answer_text = (
                ("تنطبق قاعدة معتمدة على جانب واحد من هذه المعاملة، لكن نتيجة قاعدة واحدة ليست حكمًا شاملًا. "
                 "تبقى مراجعة شرعية للنتيجة والضوابط المتبقية قبل أي خلاصة." if language == "ar" else
                 "An approved rule applies to one aspect of this transaction, but a single rule's result is not an "
                 "overall ruling. A scholar review of that result and the remaining required checks is still pending "
                 "before any conclusion.") if rule_evaluated else ("المعلومات المتاحة لا تكفي لتقييم المعاملة. أحتاج العقد أو بيان السداد الذي يوضح جهة التمويل "
                           "وكامل شروط الدفع، ثم مطابقة الآلية مع قاعدة معتمدة من مراجع شرعي." if language == "ar" else
                           "The available facts are insufficient to assess this transaction. I need the agreement or repayment "
                           "disclosure identifying the financier and complete payment terms, followed by a scholar-approved "
                           "rule mapping for the verified contract mechanism."))
        review = DecisionReviewRow(review_id=str(uuid4()), request_id=request_id, session_id=session_id,
                                   turn_id=turn_id, version=version, recorded_at=now, intent="described_operation",
                                   query=text, fact_snapshot=snapshot, decision=decision,
                                   fact_resolutions=resolutions,
                                   clarifying_turn=UserTurnProvenance(session_id=session_id, turn_id=turn_id,
                                       exact_text=text, recorded_at=now, version=version, scope=scope) if previous else None)
        updated = OperationConversation(session_id=session_id, transaction_id=transaction_id, snapshot=snapshot,
                                         clarification_count=count, pending_slot=pending,
                                         resolutions=(*(previous.resolutions if previous else ()), *resolutions))
        contract = AnswerContract(answer=answer_text, status=ComplianceStatus(decision.decision),
                                   clarification_question=question, reasoning_summary=reason,
                                   metadata={"response_language": language, "intent": "described_operation",
                                             "requires_scholar_review": decision.decision == "INSUFFICIENT_DATA",
                                             "decision_review": review.model_dump(mode="json"),
                                             "payment_consistency_check": payment_check,
                                             "approved_rule_evaluation": evaluation.model_dump(
                                                 mode="json", exclude={"outcome", "supporting_facts"} if evaluation.status == "evaluated" else None)})
        return contract, updated

    @staticmethod
    def _payment_check(facts):
        slots = ("down_payment", "instalment_count", "instalment_amount", "financed_or_final_price")
        if any(facts[slot].status not in {"user_reported", "observed"} for slot in slots):
            return None
        deposit, count, instalment, total = (facts[slot].value for slot in slots)
        if not all(isinstance(value, Money) for value in (deposit, instalment, total)) or type(count) is not int:
            return None
        if len({deposit.currency, instalment.currency, total.currency}) != 1:
            return {"reason": "payment_currencies_differ"}
        subtotal = deposit.amount + count * instalment.amount
        if subtotal == total.amount:
            return None  # Equality does not prove that all charges are known.
        return {"reason": "stated_total_differs_from_deposit_and_instalments",
                "scheduled_subtotal": Money(amount=subtotal, currency=deposit.currency).model_dump(mode="json"),
                "stated_total": total.model_dump(mode="json"),
                "unresolved": "fees or other payment terms may explain the difference"}

    @staticmethod
    def _does_not_know(text: str) -> bool:
        return bool(re.search(r"\b(?:I don't know|I do not know|unknown|unsure|not sure)\b|مش عارف|معرفش|لا أعرف|لا اعرف|لا أدري|لا ادري", text, re.I))

    @staticmethod
    def _starts_new_transaction(text: str) -> bool:
        for match in re.finditer(r"\b(?:different|another|new) (?:transaction|purchase|plan)\b|معاملة (?:تانية|ثانية|جديدة)|شراء جديد", text, re.I):
            prefix = re.split(r"[.!?؟;\n]", text[:match.start()])[-1]
            if not re.search(r"\b(?:not|no)\b|مش|ليس|ليست", prefix, re.I):
                return True
        return False

    @classmethod
    def _financier_reply(cls, text: str) -> str | None:
        if cls._does_not_know(text) or re.search(r"\b(?:not|either|or)\b|(?<!\w)(?:مش|ليس|او|أو)(?!\w)", text, re.I):
            return None
        normalized = text.strip(" .!،")
        if re.fullmatch(r"(?:the )?(?:store|seller)(?: itself)?|المحل(?: نفسه)?|البائع(?: نفسه)?", normalized, re.I):
            return normalized
        if re.fullmatch(r"(?:a |the )?(?:bank|finance company)|بنك|شركة تمويل", normalized, re.I):
            return normalized
        if re.search(r"\b(?:please|continue|yes|no|thanks|okay|ok|unknown|help)\b|شكرا|كمل|تمام|نعم|لا أعرف|مش متأكد", normalized, re.I):
            return None
        if re.fullmatch(r"[A-Z][A-Za-z&'-]*(?:\s+[A-Z][A-Za-z&'-]*){0,3}|[\u0621-\u064a]+(?:\s+[\u0621-\u064a]+){0,3}", normalized):
            return normalized  # User-reported name only, never entity resolution.
        return None
