import asyncio
from src.chatbot.contract_family_router import ContractFamilyRouter

router = ContractFamilyRouter()

queries = [
    "هل يجوز إعادة جدولة المرابحة بإضافة هامش ربح جديد على الرصيد المتبقي؟", # GC-017
    "في المشاركة المتناقصة، من يتحمل خسارة رأس المال الناتجة عن انخفاض قيمة الأصل؟", # GC-018
    "هل يجوز للكفيل (الضامن) تقاضي أجر أو عمولة مقابل الكفالة؟", # GC-019
]

with open("router_out.txt", "w", encoding="utf-8") as f:
    for q in queries:
        res = router.classify(q)
        f.write(f"\nQuery: {q}\n")
        f.write(f"Primary: {res.primary_family}\n")
        f.write(f"Confidence: {res.confidence}\n")
        f.write(f"Mode: {res.mode}\n")
        f.write(f"Signals: {res.signals}\n")
