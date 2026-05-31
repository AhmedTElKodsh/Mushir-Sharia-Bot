import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.chatbot.contract_family_router import ContractFamily


from src.config.logging_config import setup_logging
from src.models.session import ClarificationState, SessionState

logger = setup_logging()


REQUIRED_VARIABLES = {
    "loan": ["principal_amount", "interest_rate", "term_months", "purpose"],
    "investment": ["company_activity", "non_compliant_revenue_percent"],
    "purchase": ["item_type", "price", "payment_terms", "delivery_terms"],
    "contract": ["contract_type", "parties", "obligations", "duration"],
    # Islamic contract types — each requires type-specific facts before routing to retrieval
    "istisna": ["subject_matter", "delivery_terms", "penalty_clause_present"],  # AC-ISTISNA-01..03
    "ijarah": ["asset_type", "lease_term"],                                       # AC-IJARAH-01..02
    "wakalah": ["investment_scope"],                                              # AC-WAKALAH-01
    "kafalah": ["guaranteed_obligation_type"],                                    # AC-KAFALAH-01
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
    # Islamic contract types
    "subject_matter": "What is the subject of the Istisna contract? (What is being manufactured or constructed?)",
    "penalty_clause_present": "Does the contract include a penalty clause for late delivery?",
    "asset_type": "What type of asset is being leased? (real estate, vehicle, equipment?)",
    "lease_term": "What is the duration of the Ijara lease?",
    "investment_scope": "What is the investment scope of the Wakalah? Are there any restrictions on the agent?",
    "guaranteed_obligation_type": "What obligation does the Kafala guarantee? (debt, performance, quality?)",
}

QUESTION_TEMPLATES_AR = {
    "principal_amount": "ما هو المبلغ الأصلي للقرض أو التمويل؟",
    "interest_rate": "ما هو معدل الفائدة أو الربح المطلوب، إن وجد؟",
    "term_months": "ما هي مدة القرض بالأشهر؟",
    "purpose": "ما هو الغرض من هذا القرض أو التمويل؟",
    "company_activity": "ما هو نشاط الشركة أو المشروع المعني؟",
    "non_compliant_revenue_percent": "ما النسبة المئوية للإيرادات التي مصدرها حرام أو غير متوافق مع الشريعة؟",
    "item_type": "ما هو نوع السلعة أو الأصل المراد شراؤه؟",
    "price": "ما هو سعر الشراء؟",
    "payment_terms": "ما هي شروط الدفع؟",
    "delivery_terms": "هل تملك البنك السيارة وقبضها أو تحمل مخاطرها قبل بيعها لك؟",
    "contract_type": "ما نوع العقد المطلوب تقييمه؟",
    "parties": "من هم أطراف العقد؟",
    "obligations": "ما هي الالتزامات الرئيسية في هذا العقد؟",
    "duration": "ما هي مدة العقد؟",
    # Islamic contract types
    "subject_matter": "ما موضوع عقد الاستصناع؟ (ما الذي يُطلب تصنيعه أو بناؤه؟)",
    "penalty_clause_present": "هل يتضمن العقد شرطاً جزائياً على التأخير في التسليم؟",
    "asset_type": "ما نوع الأصل محل الإجارة؟ (عقار، سيارة، معدات؟)",
    "lease_term": "ما هي مدة عقد الإجارة؟",
    "investment_scope": "ما نطاق استثمار الوكالة؟ وما القيود المفروضة على الوكيل؟",
    "guaranteed_obligation_type": "ما الالتزام الذي تكفله عقد الكفالة؟ (دَيْن، أداء، جودة؟)",
}


class ClarificationEngine:
    """Collects the minimum facts needed before sending a query to RAG."""

    def __init__(self, max_clarification_turns: int = 2):
        self.max_clarification_turns = max_clarification_turns
        self.operation_keywords = {
            # English keywords
            "loan": ["loan", "borrow", "lend", "credit", "financing", "qard"],
            "investment": ["invest", "investment", "shares", "stock", "equity", "mudarabah", "musharakah"],
            "purchase": ["buy", "bought", "purchase", "acquire", "sell", "murabahah", "installment", "instalment"],
            "contract": ["contract", "agreement"],
            "istisna": ["istisna", "manufacturing", "construction"],
            "ijarah": ["ijarah", "lease", "rent", "leasing"],
            "wakalah": ["wakalah", "agency", "agent"],
            "kafalah": ["kafalah", "guarantee"],
        }
        # Arabic keywords including Modern Standard Arabic and common عامية
        self.operation_keywords_ar = {
            "loan": ["قرض", "قروض", "اقتراض", "تمويل", "ائتمان", "دين"],
            "investment": [
                "استثمار", "استثمارات", "مضاربة", "أسهم", "حصص",
                "صناديق", "ملكية", "شراكة", "مشاركة",
            ],
            "purchase": [
                "بيع", "شراء", "اشتريت", "أشتري", "اشتري", "اقتناء", "مرابحة", "تقسيط",
                "بالتقسيط", "سيارة", "عربية", "بضاعة", "سلعة", "عقار",
            ],
            "contract": ["عقد", "اتفاقية"],
            "istisna": ["استصناع", "مقاولة", "مقاولات", "تصنيع"],
            "ijarah": ["إجارة", "أجرة", "إيجار", "تأجير"],
            "wakalah": ["وكالة", "توكيل", "وكيل"],
            "kafalah": ["كفالة", "ضمان", "كفيل"],
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
            item_type = self._extract_purchase_item(text_clean)
            price = self._extract_price_amount(text_clean)
            if item_type:
                variables.setdefault("item_type", item_type)
            if price is not None:
                variables.setdefault("price", price)
            elif any(marker in text_lower for marker in ["disclosed markup", "disclosed mark-up", "known markup", "known mark-up"]):
                variables.setdefault("price", "disclosed markup")
            if any(word in text_lower for word in [
                "deferred", "installment", "instalment", "cash", "credit", "payable", "payment",
                "تقسيط", "بالتقسيط", "دفعة", "دفعات", "السداد", "قسط", "أقساط", "اقساط",
            ]):
                variables.setdefault("payment_terms", text_clean)
            if self._mentions_delivery_or_resale_sequence(text_lower):
                variables.setdefault("delivery_terms", text_clean)

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
        session_state.metadata.setdefault("response_language", self._detect_language(query))

        expected_variable = session_state.metadata.get("awaiting_variable")
        op_type = self.extract_operation_type(query) or session_state.extracted_variables.get("operation_type")

        if not op_type:
            session_state.missing_variables = ["operation_type"]
            lang = session_state.metadata.get("response_language", "en")
            if lang == "ar":
                clarify_msg = "ما نوع المعاملة المطلوب تقييمها: قرض، استثمار، شراء، أم عقد؟"
            else:
                clarify_msg = "What type of transaction is this: loan, investment, purchase, or contract?"
            if lang == "ar":
                clarify_msg = "ما نوع المعاملة المطلوب تقييمها: قرض، استثمار، شراء، أم عقد؟"
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

    def ask_if_needed(
        self,
        query: str,
        session_id: Optional[str] = None,
        known_contract_family: Optional["ContractFamily"] = None,
    ) -> Optional[str]:
        """Return a clarifying question if the query needs more facts, else None.

        Provides the stateless interface that ApplicationService requires.
        Creates a transient SessionState scoped to this single call so repeated
        invocations with the same query are idempotent.

        Args:
            query: The raw user query.
            session_id: Optional session identifier for logging.
            known_contract_family: Contract family already resolved by ContractFamilyRouter.
                When provided and the query is a judgment query (حكم/يجوز/ربوي),
                clarification is bypassed because the contract context is already known.
                When None, judgment queries still require clarification — the system
                cannot rule on a clause without knowing the contract type first.
                This guards against the false-fatwa path (AC-CE-001).
        """
        # Gate: judgment bypass ONLY fires when contract family is already confidently resolved.
        # AMBIGUOUS means the router could not determine the family, so even judgment queries
        # must go through process_query to ask for the contract type first.
        # Without this check, "ما حكم التورق المصرفي؟" would bypass clarification even
        # though organized vs. unorganised Tawarruq have completely different rulings.
        from src.chatbot.contract_family_router import ContractFamily
        _ambiguous_families = {ContractFamily.AMBIGUOUS, None}
        if self._is_judgment_query(query) and known_contract_family not in _ambiguous_families:
            return None
        if self._is_informational_query(query):
            return None
        if self._has_specific_transaction_structure(query):
            return None
        # Named-instrument bypass: a judgment query that explicitly names a specific
        # Islamic finance instrument is self-contained — the instrument resolves the
        # ambiguity. No clarification is needed even when the router returns AMBIGUOUS.
        # NOTE: Tawarruq is excluded because organized vs. unorganised Tawarruq have
        # different rulings and DO require clarification (GC-002).
        # Bay al-Wafa and fixed-distribution Sukuk are excluded because they are
        # genuinely disputed concepts (GC-013, GC-014).
        if self._is_judgment_query(query) and self._names_specific_instrument(query):
            return None
        # Second bypass: if the router has already confidently resolved the contract family,
        # skip the process_query loop entirely. The contract type IS already known from the
        # container pattern match — there's no value in asking "what type of contract is this?".
        # This covers conditional/factual questions (e.g. GC-004 MUDHARABA, GC-016 IJARA)
        # that lack explicit judgment keywords but are fully scoped by the router.
        from src.chatbot.contract_family_router import ContractFamily
        _ambiguous_families = {ContractFamily.AMBIGUOUS, None}
        if known_contract_family not in _ambiguous_families:
            return None
        try:
            state = SessionState(session_id=session_id or "")
            result = self.process_query(state, query)
            if result.get("status") == "clarifying":
                questions = result.get("questions", [])
                return questions[0] if questions else None
        except Exception as exc:
            logger.warning("Clarification check failed for query: %s", exc)
        return None

    @staticmethod
    def _is_judgment_query(query: str) -> bool:
        terms = (
            r"\bruling\b",
            r"\bpermissible\b",
            r"\bhalal\b",
            r"\bharam\b",
            r"\busury\b",
            r"\busurious\b",
            r"\bvalid\b",
            r"\binvalid\b",
            "حكم",  # حكم
            "يجوز",  # يجوز
            "جائز",  # جائز
            "حلال",  # حلال
            "حرام",  # حرام
            "ربوي",
            "ربا",
            "فاسد",
            "مخالف",
        )
        lowered = (query or "").lower()
        return any(re.search(term if term.isascii() else re.escape(term), lowered) for term in terms)

    def _clarification_turns(self, session_state: SessionState) -> int:
        """Count clarification turns, recognising both ASCII '?' and Arabic '\u061f'."""
        return sum(
            1
            for message in session_state.conversation_history
            if message.role == "system"
            and ("?" in message.content or "\u061f" in message.content)
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
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|percentage|بالمئة|في\s*المئة)", text, re.IGNORECASE)
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
        if match:
            return int(match.group(1))
        years = re.search(r"(\d+)\s*(?:years?|yrs?)", text, re.IGNORECASE)
        if years:
            return int(years.group(1)) * 12
        arabic_digit_years = re.search(r"(\d+)\s*(?:سنوات|سنة|عام|أعوام|اعوام)", text)
        if arabic_digit_years:
            return int(arabic_digit_years.group(1)) * 12
        arabic_number_words = {
            "سنة": 1, "سنتين": 2, "ثلاث": 3, "ثلاثة": 3, "اربع": 4, "أربع": 4,
            "خمسة": 5, "خمس": 5, "ست": 6, "ستة": 6, "سبع": 7, "سبعة": 7,
            "ثمان": 8, "ثمانية": 8, "تسع": 9, "تسعة": 9, "عشر": 10, "عشرة": 10,
        }
        for word, value in arabic_number_words.items():
            if re.search(rf"\b{word}\s*(?:سنوات|سنة|عام|أعوام|اعوام)\b", text):
                return value * 12
        return None

    def _extract_purchase_item(self, text: str) -> Optional[str]:
        patterns = (
            r"\bbought\s+(?:a|an|the)?\s*([a-z][a-z -]{1,40}?)(?:\s+from\b|\s+and\b|,|\.|$)",
            r"\bbuys?\s+(?:a|an|the)?\s*([a-z][a-z -]{1,40}?)(?:\s+and\b|,|\.|$)",
            r"\bpurchases?\s+(?:a|an|the)?\s*([a-z][a-z -]{1,40}?)(?:\s+and\b|,|\.|$)",
            r"\bsells?\s+(?:a|an|the)?\s*([a-z][a-z -]{1,40}?)(?:\s+to\b|,|\.|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                item = match.group(1).strip(" .,-")
                if item and item.lower() not in {"it", "this", "that"}:
                    return item
        if any(term in text for term in ["سيارة", "عربية"]):
            return "car"
        return None

    def _is_informational_query(self, query: str) -> bool:
        text = query.strip().lower()
        judgment_terms = (
            r"\bruling\b",
            r"\bcompliant\b",
            r"\bcompliance\b",
            r"\bpermissible\b",
            r"\ballowed\b",
            r"\bhalal\b",
            r"\bharam\b",
            r"\bvalid\b",
            r"\bcan i\b",
            r"\bshould i\b",
            "حلال",  # حلال
            "حرام",  # حرام
            "يجوز",
            "جائز",
            "متوافق",
            "حكم",
            "مخالف",
        )
        if any(re.search(term if term.isascii() else re.escape(term), text) for term in judgment_terms):
            return False
        informational_domains = (
            "accounting",
            "recognition",
            "measurement",
            "presentation",
            "disclosure",
            "reporting",
            "journal entry",
            "governance",
            "audit",
            "policy",
            "sharia board",
        )
        if any(term in text for term in informational_domains):
            return True
        starters = (
            "what is ",
            "what are ",
            "what does ",
            "what happens ",
            "explain ",
            "define ",
            "summarize ",
            "tell me about ",
            "how should ",  # accounting/procedural queries don't need contract-type clarification
            "how is ",
            "how are ",
            "how do ",
            "how does ",
        )
        if text.startswith(starters):
            return True
        arabic_starters = (
            "ما هي ",
            "ما هو ",
            "ما معنى ",
            "عرف ",
            "اشرح ",
        )
        arabic_starters = arabic_starters + ("ما هي ", "ما هو ", "ما معنى ", "عرف ", "اشرح ")
        return query.strip().startswith(arabic_starters)

    @staticmethod
    def _detect_language(query: str) -> str:
        arabic_chars = sum(1 for c in query if '\u0600' <= c <= '\u06ff')
        ratio = arabic_chars / max(len(query), 1)
        return "ar" if arabic_chars >= 12 or ratio > 0.30 else "en"

    @staticmethod
    def _names_specific_instrument(query: str) -> bool:
        """Return True when a judgment query names a specific Islamic finance instrument
        whose ruling is self-contained and deterministic (not variant-dependent).

        Instruments EXCLUDED (require clarification despite being named):
          - التورق (Tawarruq): organised vs. unorganised variants have different rulings (GC-002)
          - بيع الوفاء (Bay al-Wafa): genuinely disputed (GC-014)
          - Sukuk with fixed-distribution framing: disputed (GC-013)

        Instruments INCLUDED (clear, self-contained ruling):
          - قرض حسن with conditional benefit → Riba (GC-008)
          - الصرف الآجل / عقود الصرف → generally prohibited (GC-009)
          - Sukuk + capital guarantee → prohibited (GC-003)
          - الاستصناع الموازي → specific ruling (GC-010)
        """
        text = query.strip().lower()
        # Excluded: genuinely ambiguous instruments that require clarification
        _excluded = (
            "تورق",        # Tawarruq — organized vs. unorganized distinction needed
            "بيع الوفاء",  # Bay al-Wafa — disputed across schools
        )
        if any(excl in text for excl in _excluded):
            return False
        # For Sukuk: only self-contained if paired with capital guarantee language
        # Fixed-income distribution Sukuk is genuinely disputed → require clarification
        if "صكوك" in text or "الصكوك" in text or "sukuk" in text:
            if any(t in text for t in ("دخل ثابت", "ثابت دوري", "fixed income", "fixed periodic")):
                return False  # GC-013: fixed-distribution Sukuk → needs clarification
            return any(t in text for t in ("ضمان", "كفالة", "guarantee", "capital", "رأس المال"))
        # Sarf (foreign exchange) instruments — specific ruling independent of context
        if any(t in text for t in ("الصرف الآجل", "عقود الصرف", "صرف الآجل", "sarf", "forward currency", "forward exchange")):
            return True
        # Qard Hassan with conditions — specific ruling (covers both قرض حسن and القرض الحسن)
        if any(t in text for t in ("قرض حسن", "القرض الحسن", "qard hassan", "qard hasan", "qard")):
            return True
        # Parallel Istisna — specific ruling
        # موازٍ strips diacritics to مواز (not موازي), so we check the prefix مواز
        # to cover: استصناع موازٍ, الاستصناع الموازي, موازي, etc.
        if "استصناع" in text and ("مواز" in text or "موازي" in text or "parallel" in text):
            return True
        if "parallel istisna" in text:
            return True

        return False


    def _has_specific_transaction_structure(self, query: str) -> bool:
        text = query.strip().lower()
        if len(text.split()) < 8:
            return False
        known_structures = ("murabahah", "murabaha", "ijarah", "mudarabah", "musharakah", "sukuk", "مرابحة", "تقسيط")
        judgment_terms = ("compliant", "permissible", "allowed", "valid", "ruling", "حلال", "يجوز", "جائز", "متوافق")
        concrete_terms = (
            "disclosed markup",
            "disclosed mark-up",
            "markup",
            "payable",
            "deferred",
            "installment",
            "instalment",
            "ownership",
            "possession",
            "risk transfer",
            "delivery",
            "ثمن",
            "سعر",
            "ربح",
            "قيمة مضافة",
            "دفعة",
            "السداد",
        )
        if self._contains_late_payment_penalty(text) and any(term in text for term in known_structures):
            return True
        has_arabic = any("\u0600" <= char <= "\u06ff" for char in query)
        if has_arabic and not self._mentions_delivery_or_resale_sequence(text):
            return False
        return (
            any(term in text for term in known_structures)
            and any(term in text for term in judgment_terms)
            and any(term in text for term in concrete_terms)
        )

    def _mentions_price(self, text_lower: str) -> bool:
        return any(
            marker in text_lower
            for marker in ["price", "cost", "amount", "markup", "mark-up", "profit", "usd", "$", "سعر", "ثمن", "ربح", "جنيه"]
        )

    def _extract_price_amount(self, text: str) -> Optional[float]:
        patterns = (
            r"\b(?:price|cost|amount)\s*(?:is|of|:)?\s*(?:usd|eur|gbp|sar|aed|egp|\$)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(?:usd|eur|gbp|sar|aed|egp|\$)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dinar|dollars?|usd|eur|gbp|sar|aed|egp)\b",
            r"(?:سعر|ثمن|قيم(?:ة|ته|تها))\s*(?:السيارة|العربية)?\s*(?:هو|هي|:)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:جنيه|ريال|درهم|دينار)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None

    def _mentions_delivery_or_resale_sequence(self, text_lower: str) -> bool:
        delivery_markers = [
            "delivery", "deliver", "possession", "ownership", "risk transfer",
            "قبض", "تسليم", "تملك", "ملك", "حيازة", "مخاطر", "ضمان",
        ]
        if any(marker in text_lower for marker in delivery_markers):
            return True
        return (
            any(marker in text_lower for marker in ["bank buys", "seller buys", "institution buys"])
            and any(marker in text_lower for marker in ["sells it", "resells", "sells to"])
        )

    def _contains_late_payment_penalty(self, text_lower: str) -> bool:
        return any(
            marker in text_lower
            for marker in [
                "late fee", "late payment", "penalty", "default charge",
                "غرامة", "غرامه", "تأخير", "تاخير", "التأخير", "التاخير",
            ]
        )

    def _mentions_non_compliant_revenue(self, text_lower: str) -> bool:
        markers = ["haram", "non-compliant", "non compliant", "impermissible", "prohibited", "revenue"]
        return any(marker in text_lower for marker in markers)

    def _looks_like_company_activity(self, text_lower: str) -> bool:
        activity_markers = ["tech", "bank", "retail", "manufacturing", "software", "real estate", "trading"]
        revenue_markers = ["haram", "revenue", "%", "percent"]
        return any(marker in text_lower for marker in activity_markers) and not any(
            marker in text_lower for marker in revenue_markers
        )
