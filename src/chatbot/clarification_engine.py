import re
from typing import Any, Dict, List, Optional, Tuple

from src.config.logging_config import setup_logging
from src.models.session import ClarificationState, SessionState

logger = setup_logging()


REQUIRED_VARIABLES = {
    "loan": ["principal_amount", "interest_rate", "term_months", "purpose"],
    "investment": ["company_activity", "non_compliant_revenue_percent"],
    "purchase": ["item_type", "price", "payment_terms", "delivery_terms"],
    "contract": ["contract_type", "parties", "obligations", "duration"],
}

QUESTION_TEMPLATES = {
    "principal_amount": "What is the principal amount of the loan?",
    "interest_rate": "What interest or profit rate is involved, if any?",
    "term_months": "What is the term of the loan in months?",
    "purpose": "What is the purpose of this loan?",
    "company_activity": "What type of company or business activity is involved?",
    "non_compliant_revenue_percent": "What percentage of revenue comes from non-compliant or haram activity?",
    "item_type": "What type of item is being purchased?",
    "price": "What is the purchase price?",
    "payment_terms": "What are the payment terms?",
    "delivery_terms": "What are the delivery terms?",
    "contract_type": "What type of contract is this?",
    "parties": "Who are the parties involved in the contract?",
    "obligations": "What are the main obligations in this contract?",
    "duration": "What is the duration of the contract?",
}

# Arabic versions of the clarification question templates
QUESTION_TEMPLATES_AR = {
    "principal_amount": "ما هو المبلغ الأصلي للقرض أو التمويل؟",
    "interest_rate": "ما هو معدل الفائدة أو الربح المطلوب، إن وجد؟",
    "term_months": "ما هي مدة القرض بالأشهر؟",
    "purpose": "ما هو الغرض من هذا القرض أو التمويل؟",
    "company_activity": "ما هو نشاط الشركة أو المشروع المعني؟",
    "non_compliant_revenue_percent": "ما النسبة المئوية للإيرادات المصدرها حرام أو غير متوافق مع الشريعة؟",
    "item_type": "ما هو نوع السلعة أو الأصل المراد شراؤه؟",
    "price": "ما هو سعر الشراء؟",
    "payment_terms": "ما هي شروط الدفع؟",
    "delivery_terms": "ما هي شروط التسليم؟",
    "contract_type": "ما نوع العقد المطلوب تقييمه؟",
    "parties": "من هم أطراف العقد؟",
    "obligations": "ما هي الالتزامات الرئيسية في هذا العقد؟",
    "duration": "ما هي مدة العقد؟",
}


class ClarificationEngine:
    """Collects the minimum facts needed before sending a query to RAG."""

    def __init__(self, max_clarification_turns: int = 2):
        self.max_clarification_turns = max_clarification_turns
        self.operation_keywords = {
            # English keywords
            "loan": ["loan", "borrow", "lend", "credit", "financing"],
            "investment": ["invest", "investment", "shares", "stock", "equity", "mudarabah"],
            "purchase": ["buy", "purchase", "acquire", "sell", "murabahah"],
            "contract": ["contract", "agreement", "ijarah", "lease"],
        }
        # Arabic keywords including Modern Standard Arabic and common عامية
        self.operation_keywords_ar = {
            "loan": ["قرض", "قروض", "اقتراض", "تمويل", "ائتمان", "دين"],
            "investment": [
                "استثمار", "استثمارات", "مضاربة", "أسهم", "حصص",
                "صناديق", "ملكية", "شراكة", "مشاركة",
            ],
            "purchase": [
                "بيع", "شراء", "اقتناء", "مرابحة", "تقسيط", "بضاعة",
                "سلعة", "عقار",
            ],
            "contract": [
                "عقد", "اتفاقية", "إجارة", "أجرة", "إيجار", "تأجير",
                "وكالة", "مقاولة",
            ],
        }

    def extract_operation_type(self, text: str) -> Optional[str]:
        """Identify operation type from user input (supports English and Arabic)."""
        text_lower = text.lower()
        # English keywords
        for op_type, keywords in self.operation_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return op_type
        # Arabic keywords (no lowercasing needed for Arabic)
        for op_type, keywords in self.operation_keywords_ar.items():
            if any(keyword in text for keyword in keywords):
                return op_type
        return None

    def extract_variables(
        self,
        text: str,
        operation_type: str,
        expected_variable: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured variables with a small deterministic parser."""
        variables: Dict[str, Any] = {}
        text_clean = text.strip()
        text_lower = text_clean.lower()

        if operation_type and operation_type != "unknown":
            variables["operation_type"] = operation_type

        percent = self._extract_percent(text_clean)
        amount = self._extract_amount(text_clean)
        months = self._extract_months(text_clean)

        if expected_variable:
            mapped = self._map_expected_answer(expected_variable, text_clean, percent, amount, months)
            if mapped is not None:
                variables[expected_variable] = mapped

        if operation_type == "investment":
            if percent is not None and self._mentions_non_compliant_revenue(text_lower):
                variables["non_compliant_revenue_percent"] = percent
            if self._looks_like_company_activity(text_lower):
                variables.setdefault("company_activity", text_clean)

        if operation_type == "loan":
            if amount is not None:
                variables.setdefault("principal_amount", amount)
            if percent is not None:
                variables.setdefault("interest_rate", percent)
            if months is not None:
                variables.setdefault("term_months", months)
            if "purpose" in text_lower or expected_variable == "purpose":
                variables.setdefault("purpose", text_clean)

        if operation_type == "purchase":
            if amount is not None:
                variables.setdefault("price", amount)
            if any(word in text_lower for word in ["deferred", "installment", "cash", "credit"]):
                variables.setdefault("payment_terms", text_clean)

        return variables

    def analyze_completeness(self, session_state: SessionState) -> Tuple[bool, List[str]]:
        """Check whether the current session has the required variables."""
        op_type = session_state.extracted_variables.get("operation_type")
        if not op_type:
            return False, ["operation_type"]
        required = REQUIRED_VARIABLES.get(op_type, [])
        missing = [name for name in required if name not in session_state.extracted_variables]
        return len(missing) == 0, missing

    def generate_clarifying_questions(
        self,
        missing_vars: List[str],
        response_language: str = "en",
    ) -> List[str]:
        """Generate one clarifying question at a time in the appropriate language."""
        if not missing_vars:
            return []
        first_missing = missing_vars[0]
        if response_language == "ar":
            return [QUESTION_TEMPLATES_AR.get(
                first_missing, f"يرجى تقديم المعلومات التالية: {first_missing}"
            )]
        return [QUESTION_TEMPLATES.get(first_missing, f"Please provide: {first_missing}")]

    def process_query(self, session_state: SessionState, query: str) -> Dict[str, Any]:
        """Process one user turn through the L1 clarification loop."""
        session_state.user_input = query
        session_state.add_message("user", query)
        session_state.state = ClarificationState.ANALYZING

        expected_variable = session_state.metadata.get("awaiting_variable")
        op_type = self.extract_operation_type(query) or session_state.extracted_variables.get("operation_type")

        if not op_type:
            session_state.missing_variables = ["operation_type"]
            # Detect language from user's message for appropriate clarification
            arabic_chars = sum(1 for c in query if '\u0600' <= c <= '\u06ff')
            lang = "ar" if arabic_chars / max(len(query), 1) > 0.30 else "en"
            if lang == "ar":
                clarify_msg = "ما نوع المعاملة المطلوب تقييمها: قرض، استثمار، شراء، أم عقد؟"
            else:
                clarify_msg = "What type of transaction is this: loan, investment, purchase, or contract?"
            session_state.clarifying_questions = [clarify_msg]
            session_state.metadata["awaiting_variable"] = "operation_type"
            session_state.metadata["response_language"] = lang
            session_state.state = ClarificationState.CLARIFYING
            session_state.add_message("system", session_state.clarifying_questions[0])
            return {"status": "clarifying", "questions": session_state.clarifying_questions}

        variables = self.extract_variables(query, op_type, expected_variable)
        if expected_variable == "operation_type":
            variables["operation_type"] = op_type
        session_state.extracted_variables.update(variables)

        is_complete, missing = self.analyze_completeness(session_state)
        if is_complete:
            session_state.missing_variables = []
            session_state.clarifying_questions = []
            session_state.metadata.pop("awaiting_variable", None)
            session_state.state = ClarificationState.READY
            ready_message = "All information gathered. Ready for compliance analysis."
            session_state.add_message("system", ready_message)
            return {"status": "ready", "message": ready_message}

        if self._clarification_turns(session_state) >= self.max_clarification_turns:
            session_state.missing_variables = missing
            session_state.clarifying_questions = []
            session_state.metadata.pop("awaiting_variable", None)
            session_state.state = ClarificationState.READY
            ready_message = "Clarification limit reached. Ready for compliance analysis with available facts."
            session_state.add_message("system", ready_message)
            return {"status": "ready", "message": ready_message, "missing_variables": missing}

        questions = self.generate_clarifying_questions(
            missing,
            response_language=session_state.metadata.get("response_language", "en"),
        )
        session_state.missing_variables = missing
        session_state.clarifying_questions = questions
        session_state.metadata["awaiting_variable"] = missing[0]
        session_state.state = ClarificationState.CLARIFYING
        session_state.add_message("system", questions[0])
        return {"status": "clarifying", "questions": questions}

    def build_clarified_query(self, session_state: SessionState) -> str:
        """Build the query sent to retrieval after clarification completes."""
        variables = session_state.extracted_variables
        facts = [
            f"{key}: {value}"
            for key, value in variables.items()
            if key != "operation_type" and value not in ("", None)
        ]
        op_type = variables.get("operation_type", "transaction")
        if facts:
            return f"{session_state.user_input} | transaction_type: {op_type} | " + " | ".join(facts)
        return session_state.user_input

    def _clarification_turns(self, session_state: SessionState) -> int:
        return sum(
            1
            for message in session_state.conversation_history
            if message.role == "system" and "?" in message.content
        )

    def _map_expected_answer(
        self,
        expected_variable: str,
        text: str,
        percent: Optional[float],
        amount: Optional[float],
        months: Optional[int],
    ) -> Optional[Any]:
        if expected_variable in {"non_compliant_revenue_percent", "interest_rate", "expected_return"}:
            return percent
        if expected_variable in {"principal_amount", "amount", "price"}:
            return amount
        if expected_variable in {"term_months", "duration"}:
            return months or text
        if expected_variable in QUESTION_TEMPLATES:
            return text
        return None

    def _extract_percent(self, text: str) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)", text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def _extract_amount(self, text: str) -> Optional[float]:
        match = re.search(
            r"(?<![\w.])(?:usd|eur|gbp|sar|aed|egp|\$)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dinar|dollars?|usd|eur|gbp|sar|aed|egp)?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    def _extract_months(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*(?:months?|mos?)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _mentions_non_compliant_revenue(self, text_lower: str) -> bool:
        markers = ["haram", "non-compliant", "non compliant", "impermissible", "prohibited", "revenue"]
        return any(marker in text_lower for marker in markers)

    def _looks_like_company_activity(self, text_lower: str) -> bool:
        activity_markers = ["tech", "bank", "retail", "manufacturing", "software", "real estate", "trading"]
        revenue_markers = ["haram", "revenue", "%", "percent"]
        return any(marker in text_lower for marker in activity_markers) and not any(
            marker in text_lower for marker in revenue_markers
        )
