"""Deterministic prompt construction for AAOIFI-grounded answers."""
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Enhanced Orchestrator System Prompt  (v2)
# Based on system_role.docx guidance with additions:
#   - 3-phase chain-of-thought (CoT) workflow scaffold
#   - Bilingual output templates (English + Arabic)
#   - Arabic dialect / عامية normalization instruction
#   - Misspelling / transliteration tolerance
#   - Page-level citation requirement [FAS-X §Y, p.Z]
#   - AAOIFI knowledge-gap protocol
# ---------------------------------------------------------------------------

AAOIFI_GROUNDING_SYSTEM_PROMPT = """You are Mushir, a highly specialized Sharia Compliance Advisor.
Your sole function is to analyze financial operations against the AAOIFI (Accounting and Auditing Organization for Islamic Financial Institutions) Financial Accounting Standards (FAS) documents provided to you as context excerpts.

═══════════════════════════════════════════════════
GROUNDING & RETRIEVAL PROTOCOL
═══════════════════════════════════════════════════
1. MANDATORY RETRIEVAL: For every query you MUST review the provided AAOIFI excerpts before formulating any answer.
2. STRICT ATTRIBUTION: Every compliance statement must be tied to a specific finding in the provided excerpts.
3. KNOWLEDGE GAP: If the specific standard or section is NOT present in the provided excerpts, state:
   "I have reviewed the provided AAOIFI excerpts and cannot find the specific standard required to address this transaction. Please consult a qualified Sharia scholar."
4. NO HALLUCINATIONS: Never invent standard numbers, section numbers, or page numbers.
5. NO SPECULATION: If the provided text is silent on a specific point, admit uncertainty.

═══════════════════════════════════════════════════
INPUT NORMALIZATION (apply silently before analysis)
═══════════════════════════════════════════════════
- MISSPELLINGS: Interpret approximate English transliterations as their canonical forms:
  murabah/murabahat → Murabahah | mudaraba/mudharaba → Mudarabah | ijara/ijarah → Ijarah
  sukuk/sukuks → Sukuk | zakat/zakah → Zakat | gharar/ghrar → Gharar | riba/ribah → Riba
- ARABIC DIALECT (عامية): Accept Egyptian, Khaleeji, Levantine, and MSA Arabic.
  Map colloquial terms to their fiqh equivalents before analysis.
  Examples: فايدة/فوايد → ربا | بيع تقسيط → مرابحة | أجرة → إجارة | تمويل → تمويل إسلامي
- CODE-MIXING: Queries mixing Arabic and English are valid; process the intent, not just the surface form.

═══════════════════════════════════════════════════
CHAIN-OF-THOUGHT WORKFLOW (execute for every query)
═══════════════════════════════════════════════════
PHASE 1 — INFORMATION GATHERING
  - Identify: transaction type, financial amounts/rates, counterparty nature, contract structure.
  - If critical facts are missing that would materially affect the ruling → request clarification.
  - Do NOT proceed to Phase 2 on a vague query when specific facts are required.

PHASE 2 — EXCERPT REVIEW & MAPPING
  - Scan the provided AAOIFI excerpts for the relevant FAS standard.
  - Map the user's specific facts to the exact text found in the excerpts.
  - Identify: which standard applies, which section, and on which page the evidence appears.
  - If no relevant excerpt is found → use the Knowledge Gap Protocol.

PHASE 3 — COMPLIANCE DETERMINATION & CITATION
  - Apply the standard's requirements to the user's facts.
  - Determine: COMPLIANT / NON-COMPLIANT / CONDITIONALLY COMPLIANT.
  - Cite every claim with [FAS-X §Y.Z, p.N] (page number required when available).
  - Use verbatim quotations from the provided excerpts where possible.

═══════════════════════════════════════════════════
CITATION FORMAT (mandatory in every response)
═══════════════════════════════════════════════════
English format: [AAOIFI FAS-X, Section Y.Z, page N]   e.g. [AAOIFI FAS-28, Section 3.1, page 47]
Arabic format:  [معيار أيوفي FAS-X، القسم Y.Z، صفحة N]
Short inline:   [FAS-X §Y.Z, p.N]
At least ONE citation is required in every compliance response.

═══════════════════════════════════════════════════
PROHIBITED BEHAVIORS
═══════════════════════════════════════════════════
- Do NOT answer without citing an AAOIFI standard from the provided excerpts.
- Do NOT make up standard numbers, section numbers, or page numbers.
- Do NOT provide legal or financial advice beyond AAOIFI FAS scope.
- Do NOT issue a formal fatwa or binding religious ruling.
- Do NOT use external knowledge not found in the provided excerpts."""


# ---------------------------------------------------------------------------
# Bilingual response format templates (injected into prompt dynamically)
# ---------------------------------------------------------------------------

_FORMAT_TEMPLATE_EN = """
OUTPUT FORMAT — use these section headers exactly:

## Compliance Status
[COMPLIANT / NON-COMPLIANT / CONDITIONALLY COMPLIANT / INSUFFICIENT_DATA]

## Summary
[One-sentence summary based on the reviewed AAOIFI excerpts]

## Detailed Analysis
[Technical breakdown of the transaction against the FAS requirements]

## AAOIFI Standards Applied
- **[AAOIFI FAS-X, Section Y.Z, page N]**: "[Verbatim quotation from the excerpt]"

## Reasoning
[Precise explanation of how the retrieved text applies to this case]

## Conditions / Recommendations
- **Conditions:** [Mandatory steps for compliance, if applicable]
- **Recommendations:** [Structural changes if non-compliant]

> ⚠️ **Disclaimer**: This guidance is based strictly on the provided AAOIFI FAS excerpts.
> It does not constitute professional advice, a legal opinion, or a formal fatwa.
> Consult a qualified Sharia scholar for a binding ruling."""

_FORMAT_TEMPLATE_AR = """
تنسيق الإجابة — استخدم هذه العناوين بالضبط:

## حالة الامتثال
[متوافق / غير متوافق / متوافق بشروط / بيانات غير كافية]

## الملخص
[جملة واحدة تلخص النتيجة بناءً على مقاطع أيوفي المقدمة]

## التحليل التفصيلي
[تحليل تقني للمعاملة في ضوء متطلبات المعيار]

## معايير أيوفي المطبقة
- **[معيار أيوفي FAS-X، القسم Y.Z، صفحة N]**: "[اقتباس حرفي من المقطع]"

## التعليل
[شرح دقيق لكيفية انطباق النص المسترجع على هذه الحالة]

## الشروط / التوصيات
- **الشروط:** [الخطوات الإلزامية للامتثال، إن وجدت]
- **التوصيات:** [التعديلات البنيوية في حالة عدم الامتثال]

> ⚠️ **تنبيه مهم**: هذا التوجيه مبني حصراً على مقاطع معايير أيوفي المقدمة.
> لا يُعدّ نصيحة مهنية أو رأياً قانونياً أو فتوى شرعية ملزمة.
> استشر عالماً شرعياً مؤهلاً للحصول على حكم ملزم."""

_INCOMPLETE_QUERY_EN = """
If critical information is missing, respond with ONLY:

---
I need additional information to provide an accurate ruling based on the AAOIFI excerpts:

1. [Specific question about the missing detail]
2. [Specific question about the missing detail]

Once provided, I will review the relevant FAS standards in the provided excerpts.
---"""

_INCOMPLETE_QUERY_AR = """
إذا كانت المعلومات الجوهرية ناقصة، أجب بهذا الشكل فقط:

---
أحتاج إلى معلومات إضافية لتقديم حكم دقيق بناءً على مقاطع أيوفي:

1. [سؤال محدد عن التفاصيل الناقصة]
2. [سؤال محدد عن التفاصيل الناقصة]

بعد تقديمها، سأراجع معايير أيوفي ذات الصلة في المقاطع المقدمة.
---"""


class PromptBuilder:
    """Builds structured prompts for AAOIFI-grounded bilingual compliance analysis.

    Primary API: build_messages() returns (system_prompt, user_prompt) so the LLM
    client can send them as separate system/user role messages for optimal model
    instruction following.

    Legacy API: build() concatenates both into a single string for backward compat.
    """

    prompt_version = "l2-aaoifi-grounded-bilingual-cot-v2"

    def __init__(
        self,
        system_prompt: str = AAOIFI_GROUNDING_SYSTEM_PROMPT,
        max_history_turns: int = 3,
        max_history_chars: int = 4000,
    ):
        self.system_prompt = system_prompt
        self.max_history_turns = max_history_turns
        self.max_history_chars = max_history_chars

    # ------------------------------------------------------------------
    # Primary API: returns (system_prompt, user_prompt) tuple
    # ------------------------------------------------------------------

    def build_messages(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
        response_language: str = "en",
    ) -> Tuple[str, str]:
        """Return (system_prompt_str, user_prompt_str) for role-separated LLM calls."""
        system = self._build_system(response_language)
        user = self._build_user(query, chunks, history or [], response_language)
        return system, user

    # ------------------------------------------------------------------
    # Legacy API: concatenates system + user for single-string callers
    # ------------------------------------------------------------------

    def build(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
        response_language: str = "en",
    ) -> str:
        """Backward-compatible single-string prompt for callers not yet using build_messages."""
        system, user = self.build_messages(query, chunks, history, response_language)
        return f"{system}\n\n{user}"

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_system(self, response_language: str) -> str:
        format_template = _FORMAT_TEMPLATE_AR if response_language == "ar" else _FORMAT_TEMPLATE_EN
        incomplete_template = _INCOMPLETE_QUERY_AR if response_language == "ar" else _INCOMPLETE_QUERY_EN
        if response_language == "ar":
            lang_instruction = (
                "Language instruction:\n"
                "Respond in clear Modern Standard Arabic (فصحى). "
                "Accept and understand عامية (colloquial) Arabic input but always respond in formal Arabic. "
                "Keep AAOIFI citation tokens unchanged, e.g. [FAS-28 §3.1, p.47]."
            )
        else:
            lang_instruction = (
                "Language instruction:\n"
                "Respond in English unless the user explicitly asks otherwise. "
                "Accept Arabic, mixed, or misspelled queries — understand the intent and respond in English."
            )
        return "\n\n".join([
            self.system_prompt.strip(),
            lang_instruction,
            format_template.strip(),
            incomplete_template.strip(),
        ])

    def _build_user(
        self,
        query: str,
        chunks: List[Any],
        history: List[Dict[str, str]],
        response_language: str,
    ) -> str:
        sections = []
        rendered_history = self._format_history(history)
        if rendered_history:
            sections.append(f"Recent conversation:\n{rendered_history}")
        sections.append(f"AAOIFI excerpts:\n{self.format_chunks(chunks)}")
        sections.append(f"Current question:\n{query.strip()}")
        sections.append(
            "Apply the 3-phase workflow above. Return your compliance determination "
            "using the specified output format. "
            "Use INSUFFICIENT_DATA when the excerpts do not support an answer."
        )
        return "\n\n".join(sections)

    def format_chunks(self, chunks: List[Any]) -> str:
        if not chunks:
            return "No retrieved AAOIFI excerpts."
        formatted = []
        for index, chunk in enumerate(chunks, 1):
            text = self._chunk_text(chunk)
            standard = self._chunk_standard(chunk)
            section = self._chunk_section(chunk)
            page = self._chunk_page(chunk)
            score = self._chunk_score(chunk)
            page_info = f", p.{page}" if page else ""
            formatted.append(f"[{index}] {standard} §{section}{page_info} (score: {score:.2f})\n{text}")
        return "\n\n---\n\n".join(formatted)

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        recent = history[-self.max_history_turns :]
        lines = []
        for turn in recent:
            user = (turn.get("user") or "").strip()
            assistant = (turn.get("assistant") or "").strip()
            if user:
                lines.append(f"User: {user}")
            if assistant:
                lines.append(f"Assistant: {assistant}")
        rendered = "\n".join(lines)
        return rendered[-self.max_history_chars :]

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("content") or chunk.get("text") or "")
        return str(getattr(chunk, "text", ""))

    @staticmethod
    def _chunk_standard(chunk: Any) -> str:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return str(metadata.get("standard_number") or metadata.get("source_file") or "Unknown")
        return str(getattr(getattr(chunk, "citation", None), "standard_id", "Unknown"))

    @staticmethod
    def _chunk_section(chunk: Any) -> str:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return str(
                metadata.get("section_number")
                or metadata.get("section_title")
                or metadata.get("section")
                or "Unknown"
            )
        return str(getattr(getattr(chunk, "citation", None), "section", None) or "Unknown")

    @staticmethod
    def _chunk_page(chunk: Any) -> Optional[str]:
        """Return page number string if available, None otherwise."""
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            page = metadata.get("page_number") or metadata.get("page")
            return str(page) if page is not None else None
        citation = getattr(chunk, "citation", None)
        page = getattr(citation, "page", None)
        return str(page) if page is not None else None

    @staticmethod
    def _chunk_score(chunk: Any) -> float:
        if isinstance(chunk, dict):
            return float(chunk.get("similarity") or chunk.get("score") or 0.0)
        return float(getattr(chunk, "score", 0.0) or 0.0)
