#!/usr/bin/env python3
"""Debug script for clarification bypass — all 18 gold-set cases."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.chatbot.contract_family_router import ContractFamilyRouter
from src.chatbot.clarification_engine import ClarificationEngine

router = ContractFamilyRouter()
engine = ClarificationEngine()

cases = [
    ('GC-001', 'ما نسبة الربح المسموح بها في عقود المرابحة العقارية؟', False),
    ('GC-002', 'ما حكم التورق المصرفي؟', True),
    ('GC-003', 'هل يجوز لمصدر الصكوك ضمان رأس المال للمستثمرين؟', False),
    ('GC-004', 'هل يحق للمضارب أخذ راتب شهري مقطوع من رأس مال المضاربة؟', False),
    ('GC-005', 'اشرح مبدأ الغنم بالغرم في عقود المشاركة', False),
    ('GC-008', 'هل يجوز اشتراط منفعة على المُقرض في عقد القرض الحسن؟', False),
    ('GC-009', 'ما حكم عقود الصرف الآجل في العملات؟', False),
    ('GC-010', 'هل الاستصناع الموازي جائز شرعاً إذا التزم المصنِّع الأول؟', False),
    ('GC-011', 'إذا ضمنت المؤسسة عائداً ثابتاً لصندوق الوكالة بالاستثمار، فهل تتحول الوكالة إلى قرض؟', False),
    ('GC-013', 'هل يُعدّ الصكوك الذي يُوزّع دخلاً ثابتاً دورياً مخالفاً للمشاركة في الأرباح؟', True),
    ('GC-014', 'هل بيع الوفاء (اشتراط حق استرداد المبيع) جائز شرعاً؟', True),
    ('GC-016', 'إذا تضمّنت الإجارة ضماناً بالقيمة المتبقية للأصل عند نهاية العقد، فهل تبقى إجارة شرعية؟', False),
    ('GC-018', 'في المشاركة المتناقصة، من يتحمل خسارة رأس المال الناتجة عن انخفاض قيمة الأصل؟', False),
]

passes = fails = 0
print('case_id | expect_clarify | family | mode | judgment | instrument | ask_result')
print('-' * 90)
for case_id, q, expect_clarify in cases:
    r = router.classify(q)
    if not r:
        fails += 1
        print(f"[{case_id}] FAIL | primary=None | expected={expect_clarify}")
        continue
    aq = engine.ask_if_needed(q, known_contract_family=r.primary_family)
    actual_clarify = aq is not None
    ok = actual_clarify == expect_clarify
    mark = 'OK  ' if ok else 'FAIL'
    if ok: passes += 1
    else: fails += 1
    print(f'{case_id} [{mark}]: clarify exp={expect_clarify} act={actual_clarify} fam={r.primary_family.value:<14}')

print(f'\n{passes} PASS / {fails} FAIL')

if fails > 0:
    import sys
    sys.exit(1)
