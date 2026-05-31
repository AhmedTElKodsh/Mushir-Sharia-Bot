import pytest

from src.chatbot.contract_classifier import ContractTypeClassifier
from src.models.commercial import ContractFamily


pytestmark = pytest.mark.service


@pytest.mark.parametrize(
    ("query", "family"),
    [
        ("Is an istisna construction contract with delay damages permissible?", ContractFamily.ISTISNA),
        ("\u0647\u0644 \u0634\u0631\u0637 \u063a\u0631\u0627\u0645\u0629 \u0627\u0644\u062a\u0623\u062e\u064a\u0631 \u0641\u064a \u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0634\u0631\u0637 \u0631\u0628\u0648\u064a\u061f", ContractFamily.ISTISNA),
        ("Can we use murabaha for a car installment sale?", ContractFamily.MURABAHA),
        ("Does an ijara lease late fee need charity treatment?", ContractFamily.IJARAH),
        ("Can the bank charge for a kafalah guarantee?", ContractFamily.KAFALA),
    ],
)
def test_contract_classifier_detects_contract_family(query, family):
    result = ContractTypeClassifier().classify(query)

    assert result is not None
    assert result.contract_family == family
    assert result.confidence >= 0.72


def test_contract_classifier_returns_none_for_generic_query():
    assert ContractTypeClassifier().classify("Is this compliant?") is None
