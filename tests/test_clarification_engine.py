from src.chatbot.clarification_engine import ClarificationEngine
from src.models.session import ClarificationState, SessionState

import pytest

pytestmark = pytest.mark.service


def test_investment_clarification_collects_company_and_haram_revenue():
    engine = ClarificationEngine()
    session = SessionState(session_id="l1-investment")

    first = engine.process_query(session, "I want to invest in a company")
    assert first["status"] == "clarifying"
    assert first["questions"] == ["What type of company or business activity is involved?"]
    assert session.metadata["awaiting_variable"] == "company_activity"

    second = engine.process_query(session, "Tech company with some haram revenue")
    assert second["status"] == "clarifying"
    assert second["questions"] == [
        "What percentage of revenue comes from non-compliant or haram activity?"
    ]
    assert session.extracted_variables["company_activity"] == "Tech company with some haram revenue"
    assert session.metadata["awaiting_variable"] == "non_compliant_revenue_percent"

    third = engine.process_query(session, "About 3%")
    assert third["status"] == "ready"
    assert session.state == ClarificationState.READY
    assert session.extracted_variables["operation_type"] == "investment"
    assert session.extracted_variables["non_compliant_revenue_percent"] == 3.0
    assert "awaiting_variable" not in session.metadata


def test_unknown_operation_asks_for_transaction_type_then_continues():
    engine = ClarificationEngine()
    session = SessionState(session_id="l1-unknown")

    first = engine.process_query(session, "Can you check this?")
    assert first["status"] == "clarifying"
    assert "loan, investment, purchase, or contract" in first["questions"][0]

    second = engine.process_query(session, "It is an investment")
    assert second["status"] == "clarifying"
    assert session.extracted_variables["operation_type"] == "investment"
    assert second["questions"] == ["What type of company or business activity is involved?"]


def test_build_clarified_query_includes_collected_facts():
    engine = ClarificationEngine()
    session = SessionState(session_id="l1-query")

    engine.process_query(session, "I want to invest in a company")
    engine.process_query(session, "Software company")
    engine.process_query(session, "2.5 percent haram revenue")

    clarified_query = engine.build_clarified_query(session)
    assert "transaction_type: investment" in clarified_query
    assert "company_activity: Software company" in clarified_query
    assert "non_compliant_revenue_percent: 2.5" in clarified_query


def test_clarification_loop_stops_after_two_questions_with_available_facts():
    engine = ClarificationEngine(max_clarification_turns=2)
    session = SessionState(session_id="l1-two-turn-limit")

    first = engine.process_query(session, "Can you check this?")
    assert first["status"] == "clarifying"

    second = engine.process_query(session, "It is a loan")
    assert second["status"] == "clarifying"

    third = engine.process_query(session, "I do not know the rest yet")
    assert third["status"] == "ready"
    assert session.state == ClarificationState.READY
    assert "missing_variables" in third
    assert "awaiting_variable" not in session.metadata


def test_murabaha_purchase_with_resale_sequence_is_ready_for_retrieval():
    engine = ClarificationEngine()
    query = (
        "In a murabaha sale, the bank buys a car and sells it to the customer "
        "at a disclosed markup payable over 24 months."
    )

    session = SessionState(session_id="l1-murabaha")
    result = engine.process_query(session, query)

    assert result["status"] == "ready"
    assert session.extracted_variables["operation_type"] == "purchase"
    assert session.extracted_variables["item_type"] == "car"
    assert "payment_terms" in session.extracted_variables
    assert "delivery_terms" in session.extracted_variables
    assert session.extracted_variables["price"] == "disclosed markup"
    assert engine.ask_if_needed(query) is None


def test_informational_murabaha_question_skips_transaction_clarification():
    engine = ClarificationEngine()

    assert (
        engine.ask_if_needed(
            "What does AAOIFI say about executing a Murabaha transaction in foreign currency?"
        )
        is None
    )


def test_judgment_query_with_missing_facts_asks_one_targeted_question():
    engine = ClarificationEngine()

    question = engine.ask_if_needed("What is the ruling on my investment?")

    assert question == "What type of company or business activity is involved?"
    assert question.count("?") == 1


def test_specific_murabaha_compliance_query_skips_extra_clarification():
    engine = ClarificationEngine()

    assert (
        engine.ask_if_needed(
            "Is a Murabaha sale with disclosed markup payable over 24 months compliant?"
        )
        is None
    )


def test_arabic_definition_question_skips_transaction_clarification():
    engine = ClarificationEngine()

    assert engine.ask_if_needed("ما هي المرابحة؟") is None


def test_arabic_transaction_clarification_uses_arabic_question():
    engine = ClarificationEngine()

    question = engine.ask_if_needed("أريد شراء سيارة بالمرابحة")

    assert question == "ما هو نوع السلعة أو الأصل المراد شراؤه؟"
