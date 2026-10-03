"""Arabic phrasings that ask for a judgment without a halal/haram keyword (deferred-work item 8)."""
import pytest

from src.chatbot.commercial_assessment import ScenarioExtractor
from src.models.commercial import QuestionType


@pytest.mark.parametrize("query", [
    "هل يحق للمضارب أخذ راتب شهري مقطوع من رأس مال المضاربة؟",
    "هل يصح عقد المرابحة قبل تملك البنك للسلعة؟",
    "إذا ضمنت المؤسسة عائداً ثابتاً لصندوق الوكالة بالاستثمار، فهل تتحول الوكالة إلى قرض؟",
    "هل يتحول عقد الإجارة إلى بيع إذا ضمن المستأجر القيمة المتبقية؟",
    "في المشاركة المتناقصة، من يتحمل خسارة رأس المال الناتجة عن انخفاض قيمة الأصل؟",
])
def test_arabic_judgment_asks_are_permissibility(query):
    assert ScenarioExtractor().extract(query).question_type == QuestionType.PERMISSIBILITY


@pytest.mark.parametrize("query", [
    "ما هي المعالجة المحاسبية للمضاربة؟",
    "كيف يتم الإفصاح عن المشاركة المتناقصة في القوائم المالية؟",
])
def test_accounting_questions_stay_accounting(query):
    assert ScenarioExtractor().extract(query).question_type == QuestionType.ACCOUNTING
