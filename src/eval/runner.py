import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from tests.eval.gold_set import GoldSet, GoldCase
# In the future, this will import the new LayeredScenarioExtractor.
# For now, we mock the runner interface to establish the TDD baseline.
# We will run this against the actual router in Part 2.

class EvalRunner:
    def __init__(self):
        self.gold_set = GoldSet()
        
    def evaluate_case(self, case: GoldCase) -> bool:
        """
        Evaluate a single case against the current routing logic.
        Since we are in TDD mode (Red Phase), this will simulate
        the current failure mode for the Istisna delay penalty case.
        """
        # Placeholder for actual routing logic injection
        # e.g., router = StandardsRouter()
        # intent = router.extract_intent(case.query_ar)
        
        import sys
        # ensure stdout can handle utf-8
        sys.stdout.reconfigure(encoding='utf-8')
        print(f"Evaluating Case {case.id}: {case.query_ar}")
        
        from src.chatbot.scenario_extractor import LayeredScenarioExtractor
        extractor = LayeredScenarioExtractor()
        intent = extractor.extract_intent(case.query_ar)
        actual_family = intent.contract_family.value
        
        if actual_family != case.expected_contract_family:
            print(f"  [FAIL] Expected {case.expected_contract_family}, got {actual_family}")
            return False
            
        print(f"  [PASS] Successfully classified as {actual_family}")
        return True

    def run_tier_1(self):
        print("Running Tier 1 Authoritative Cases...")
        cases = self.gold_set.get_tier_1_cases()
        passed = 0
        for case in cases:
            if self.evaluate_case(case):
                passed += 1
                
        print(f"Tier 1 Results: {passed}/{len(cases)} passed.")
        return passed == len(cases)

if __name__ == "__main__":
    runner = EvalRunner()
    success = runner.run_tier_1()
    sys.exit(0 if success else 1)
