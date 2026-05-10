from src.chatbot.clarification_engine import ClarificationEngine
from src.models.session import ClarificationState, SessionState


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
