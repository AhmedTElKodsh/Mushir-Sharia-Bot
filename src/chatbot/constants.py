"""Shared constants across chatbot and RAG modules."""
AUTHORITY_REQUEST_TERMS = (
    "binding fatwa", "binding ruling", "legal advice", "financial advice",
    "\u0641\u062a\u0648\u0649 \u0645\u0644\u0632\u0645\u0629",  # فتوى ملزمة
    "\u062d\u0643\u0645 \u0634\u0631\u0639\u064a \u0645\u0644\u0632\u0645",  # حكم شرعي ملزم
    "\u0646\u0635\u064a\u062d\u0629 \u0642\u0627\u0646\u0648\u0646\u064a\u0629",  # نصيحة قانونية
    "\u0646\u0635\u064a\u062d\u0629 \u0645\u0627\u0644\u064a\u0629",  # نصيحة مالية
)