import pytest
from src.institution_db.schema import InstitutionScraper, ComplianceCrossReferencer

@pytest.mark.unit
def test_institution_scraper_scaffold_returns_placeholder():
    scraper = InstitutionScraper()
    operations = scraper.scrape_operations()
    
    assert len(operations) == 1
    assert operations[0].operation_id == "placeholder_1"
    assert operations[0].institution_name == "Example Islamic Bank"
    assert operations[0].operation_title == "New Car Murabaha"
    assert operations[0].compliance_status == "UNVERIFIED"

@pytest.mark.unit
def test_compliance_cross_referencer_scaffold_mutates_status():
    scraper = InstitutionScraper()
    referencer = ComplianceCrossReferencer()
    
    operation = scraper.scrape_operations()[0]
    assessed_operation = referencer.assess_compliance(operation)
    
    assert assessed_operation.mapped_aaoifi_contract == "MURABAHA"
    assert assessed_operation.compliance_status == "PENDING_SCHOLAR_REVIEW"
