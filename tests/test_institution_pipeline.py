from datetime import date
import csv
import zipfile

import pytest

pytestmark = pytest.mark.service

from src.governance import (
    AccessControlDecision,
    AccessControlSignal,
    AaoifiMappingGenerator,
    ArtifactFetchRequest,
    ArtifactClassifier,
    ArtifactClass,
    CorpusPilotGate,
    CorpusPilotPlan,
    DiscoveryBudget,
    DiscoveryEvidenceCandidate,
    DiscoveryEvidenceType,
    EngineAssessmentCsvStore,
    ExtractionStatus,
    FetchResponse,
    InstitutionDiscoveryStatus,
    InstitutionRegulator,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionSector,
    LocalArtifactStore,
    OfficialSiteDiscoveryRunner,
    OperationFamily,
    OperationEvidenceField,
    OperationExtractor,
    PromotionStage,
    PublicArtifactAuthorityRank,
    PublicArtifactRecord,
    PublicArtifactFetcher,
    PublicArtifactType,
    ReviewCandidateStatus,
    ScholarReviewCsvStore,
    ScholarReviewListCsvStore,
    ScholarReviewRecord,
    WorkbookRegistryLoader,
    normalize_evidence_text,
)


def test_workbook_registry_loader_reads_controlled_xlsx_rows(tmp_path):
    workbook = tmp_path / "institutions.xlsx"
    _write_minimal_xlsx(
        workbook,
        {
            "01_CBE_Banks": [
                ["Institution Name", "Website"],
                ["Faisal Islamic Bank of Egypt", "https://www.faisalbank.com.eg/"],
            ],
            "03_Insurance": [
                ["Company Name", "Sector"],
                ["Delta Insurance", "insurance"],
            ],
            "02_Capital_Market": [
                ["#", "Name", "Name (English)", "Name (Arabic)", "Source"],
                ["1", "شركه صندوق استثمار مصر العقاري 1", "", "شركه صندوق استثمار مصر العقاري 1", "FRA"],
                ["2", "شركه صندوق استثمار صواري فينشرز مصر 1", "", "شركه صندوق استثمار صواري فينشرز مصر 1", "FRA"],
            ],
        },
    )

    registry = WorkbookRegistryLoader().load_xlsx(workbook)

    bank = registry.get("cbe-bank-faisal-islamic-bank-of-egypt")
    insurer = registry.get("fra-insurance-delta-insurance")
    assert bank.regulator == InstitutionRegulator.CBE
    assert bank.official_website == "https://www.faisalbank.com.eg/"
    assert bank.baseline_inputs == ["Egypt_Financial_Institutions_COMPLETE.xlsx"]
    assert insurer.sector == InstitutionSector.INSURANCE
    assert len(registry.records()) == 4
    assert len({record.institution_id for record in registry.records()}) == 4


def test_workbook_registry_loader_does_not_guess_name_from_status_columns():
    registry = WorkbookRegistryLoader().load_mappings(
        [
            {
                "Status": "Licensed",
                "Source": "FRA",
                "Website": "https://example.com/status-only",
            }
        ],
        "03_Insurance",
    )

    assert registry.records() == []


def test_discovery_runner_caps_candidates_and_never_infers_urls():
    record = InstitutionRegistryRecord.baseline(
        name_en="Hard Case Finance",
        regulator=InstitutionRegulator.FRA,
        sector=InstitutionSector.CONSUMER_FINANCE,
        registry_source="FRA financing register",
        registry_source_url="https://fra.gov.eg/",
    )
    runner = OfficialSiteDiscoveryRunner(
        DiscoveryBudget(max_regulator_links=1, max_search_results=2, max_manual_candidates=1, max_total_attempts=3)
    )
    candidates = [
        DiscoveryEvidenceCandidate(
            url=f"https://example{i}.com",
            evidence_type=DiscoveryEvidenceType.SEARCH_RESULT,
            confidence=0.1 + i / 100,
            status=InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
        )
        for i in range(5)
    ]

    result = runner.run(record, candidates, checked_at=date(2026, 5, 20))

    assert result.status == InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED
    assert result.selected_url is None
    assert len(result.attempts) == 2
    assert result.stop_reason.value == "max_attempts_reached"


def test_discovery_runner_confirms_official_site_from_supplied_evidence_only():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    result = OfficialSiteDiscoveryRunner().run(
        record,
        [
            DiscoveryEvidenceCandidate(
                url="https://www.faisalbank.com.eg/",
                evidence_type=DiscoveryEvidenceType.REGULATOR_LINK,
                confidence=0.98,
                status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
                notes="CBE register link matched institution name.",
            )
        ],
        checked_at=date(2026, 5, 20),
    )

    assert result.selected_url == "https://www.faisalbank.com.eg/"
    assert result.confidence == 0.98
    assert result.to_registry_updates()["attempt_count"] == 1


def test_public_artifact_fetcher_obeys_access_control_and_stores_allowed_artifacts(tmp_path):
    request = ArtifactFetchRequest(
        institution_id="cbe-bank-faisal-islamic-bank-of-egypt",
        url="https://www.faisalbank.com.eg/murabaha",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.TERMS,
        language="en",
    )
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return FetchResponse(
            status_code=200,
            content_type="text/html",
            body=b"<html><body>Murabaha terms include late payment charity fees.</body></html>",
        )

    fetcher = PublicArtifactFetcher(fake_fetch, LocalArtifactStore(tmp_path))
    allowed = AccessControlDecision.evaluate(url=request.url, checked_at=date(2026, 5, 20))

    artifact = fetcher.fetch(request, allowed, retrieved_at=date(2026, 5, 20))

    assert calls == [request.url]
    assert artifact.extraction_status.value == "extracted"
    assert (tmp_path / artifact.raw_path).exists()
    assert "Murabaha terms" in (tmp_path / artifact.text_path).read_text(encoding="utf-8")


def test_public_artifact_fetcher_records_blocked_sites_without_fetching(tmp_path):
    request = ArtifactFetchRequest(
        institution_id="fra-non-bank-finance-hard-case-finance",
        url="https://blocked.example/contracts",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.CONTRACT,
    )
    fetcher = PublicArtifactFetcher(
        lambda url: (_ for _ in ()).throw(AssertionError("fetch should not run")),
        LocalArtifactStore(tmp_path),
    )
    blocked = AccessControlDecision.evaluate(
        url=request.url,
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.SECURITY_BLOCK],
        reason="Site presents an anti-bot challenge before public content.",
    )

    artifact = fetcher.fetch(request, blocked, retrieved_at=date(2026, 5, 20))

    assert artifact.extraction_status.value == "blocked_by_security"
    assert artifact.raw_path is None
    assert artifact.text_path is None


def test_operation_extractor_and_mapping_generator_prepare_scholar_review():
    artifact = _artifact("art-1", "cbe-bank-faisal-islamic-bank-of-egypt")
    text = (
        "Murabaha deferred payment product. The bank purchases the asset, transfers ownership, "
        "charges fees, and late payment amounts go to charity."
    )

    operation = OperationExtractor().extract(
        institution_id=artifact.institution_id,
        artifact=artifact,
        text=text,
    )
    mapping = AaoifiMappingGenerator().generate(operation)

    assert OperationEvidenceField.OWNERSHIP_OR_ASSET_FLOW in operation.fields_present()
    assert OperationEvidenceField.LATE_PAYMENT_CLAUSES in operation.fields_present()
    assert mapping.status.value == "machine_proposed"
    assert "FAS-28" in mapping.candidate_standards
    assert "SS-08" in mapping.candidate_standards
    assert mapping.risk_label.value == "high"


def test_lightweight_evidence_normalization_preserves_arabic_and_english_signal():
    raw = " مُرَابَحَة ١٢٣ ــ AL-Murabaha TERMS "

    normalized = normalize_evidence_text(raw)

    assert normalized.raw_text == raw
    assert normalized.normalized_text == "مرابحة 123 al-murabaha terms"
    assert normalized.detected_language == "mixed"


def test_artifact_classifier_identifies_product_reports_blocked_and_unknown():
    classifier = ArtifactClassifier()

    assert classifier.classify(
        text="Retail murabaha product finance terms and conditions",
        artifact_type=PublicArtifactType.PRODUCT_PAGE,
        extraction_status=ExtractionStatus.EXTRACTED,
        url="https://bank.example/murabaha",
    ) == ArtifactClass.PRODUCT_PAGE
    assert classifier.classify(
        text="Annual report audited financial statements",
        artifact_type=PublicArtifactType.ANNUAL_REPORT,
        extraction_status=ExtractionStatus.EXTRACTED,
        url="https://bank.example/reports/annual-report.pdf",
    ) == ArtifactClass.ANNUAL_REPORT
    assert classifier.classify(
        text="Site presents an anti-bot challenge",
        artifact_type=PublicArtifactType.OTHER,
        extraction_status=ExtractionStatus.BLOCKED_BY_SECURITY,
        url="https://bank.example/contracts",
    ) == ArtifactClass.BLOCKED_OR_UNUSABLE
    assert classifier.classify(
        text="Welcome to our website",
        artifact_type=PublicArtifactType.OTHER,
        extraction_status=ExtractionStatus.EXTRACTED,
        url="https://bank.example/",
    ) == ArtifactClass.UNKNOWN
    assert classifier.classify(
        text="Please log in to continue to this secure page",
        artifact_type=PublicArtifactType.PRODUCT_PAGE,
        extraction_status=ExtractionStatus.EXTRACTED,
        url="https://bank.example/login",
    ) == ArtifactClass.BLOCKED_OR_UNUSABLE
    assert classifier.classify(
        text="This content is behind a paywall and requires subscription",
        artifact_type=PublicArtifactType.TERMS,
        extraction_status=ExtractionStatus.PARTIAL,
        url="https://bank.example/terms",
    ) == ArtifactClass.BLOCKED_OR_UNUSABLE


def test_operation_extractor_uses_ontology_fields_and_preserves_review_evidence():
    artifact = _artifact("art-ontology", "cbe-bank-faisal-islamic-bank-of-egypt")
    text = (
        "تمويل مرابحة للسيارات. The bank purchases the asset before sale. "
        "Late payment amounts go to charity."
    )

    operation = OperationExtractor().extract(
        institution_id=artifact.institution_id,
        artifact=artifact,
        text=text,
        operation_name="Car finance",
    )

    assert operation.raw_text == text
    assert "مرابحة" in operation.normalized_text
    assert operation.detected_language == "mixed"
    assert operation.artifact_class == ArtifactClass.PRODUCT_PAGE
    assert operation.operation_family == OperationFamily.MURABAHA
    assert operation.normalized_operation == "murabaha"
    assert operation.confidence > 0
    assert "murabaha" in operation.matched_aliases
    assert operation.evidence_snippet
    assert operation.needs_review_reason == "machine_proposed_requires_scholar_review"
    assert operation.runtime_eligible is False
    assert operation.promotion_stage.value == "mapped_machine_proposed"


def test_operation_extractor_routes_false_positive_to_unknown_review():
    artifact = _artifact("art-news", "cbe-bank-faisal-islamic-bank-of-egypt")

    operation = OperationExtractor().extract(
        institution_id=artifact.institution_id,
        artifact=artifact,
        text="The finance department published investment news and careers updates.",
    )

    assert operation.operation_family == OperationFamily.UNKNOWN
    assert operation.confidence == 0.0
    assert operation.matched_aliases == []
    assert operation.needs_review_reason == "no_governed_operation_family_detected"


def test_operation_extractor_does_not_map_please_to_ijarah_lease():
    artifact = _artifact("art-please", "cbe-bank-faisal-islamic-bank-of-egypt")

    operation = OperationExtractor().extract(
        institution_id=artifact.institution_id,
        artifact=artifact,
        text="Please contact customer service for product information and office hours.",
    )

    assert operation.operation_family == OperationFamily.UNKNOWN
    assert "lease" not in operation.matched_aliases


def test_public_artifact_fetcher_fails_closed_on_cross_domain_redirect(tmp_path):
    request = ArtifactFetchRequest(
        institution_id="cbe-bank-faisal-islamic-bank-of-egypt",
        url="https://bank.example/murabaha",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.PRODUCT_PAGE,
        language="en",
    )
    fetcher = PublicArtifactFetcher(
        lambda url: FetchResponse(
            status_code=200,
            content_type="text/html",
            body=b"<html>Murabaha deferred payment product</html>",
            final_url="https://login.vendor.example/murabaha",
        ),
        LocalArtifactStore(tmp_path),
    )

    artifact = fetcher.fetch(
        request,
        AccessControlDecision.evaluate(url=request.url, checked_at=date(2026, 5, 24)),
        retrieved_at=date(2026, 5, 24),
    )

    assert artifact.url == request.url
    assert artifact.extraction_status == ExtractionStatus.BLOCKED_BY_SECURITY
    assert artifact.artifact_class == ArtifactClass.BLOCKED_OR_UNUSABLE
    assert "cross-domain redirect" in artifact.notes
    assert artifact.raw_path is None


def test_registry_excludes_blocked_artifacts_from_evidence_priority():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    blocked = _artifact("art-blocked", record.institution_id)
    blocked = PublicArtifactRecord.from_mapping(
        {
            **blocked.to_dict(),
            "artifact_class": ArtifactClass.BLOCKED_OR_UNUSABLE.value,
        }
    )
    registry = InstitutionRegistry([record])
    registry.add_artifact(blocked)

    assert registry.evidence_artifacts_for(record.institution_id) == []


def test_scholar_review_csv_import_and_gold_case_generation(tmp_path):
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = PublicArtifactRecord.from_mapping(
        {
            **_artifact("art-1", record.institution_id).to_dict(),
            "artifact_type": PublicArtifactType.CONTRACT.value,
            "artifact_class": ArtifactClass.TERMS_OR_CONTRACT.value,
        }
    )
    operation = OperationExtractor().extract(
        institution_id=record.institution_id,
        artifact=artifact,
        text="Murabaha terms include bank purchases and ownership transfer.",
    )
    mapping = AaoifiMappingGenerator().generate(operation)
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)
    registry.add_operation(operation)
    registry.add_machine_mapping(mapping)
    candidate_path = tmp_path / "candidates.csv"
    review_path = tmp_path / "reviews.csv"

    ScholarReviewCsvStore.export_candidates(candidate_path, registry.machine_mappings())
    with review_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "review_id",
                "mapping_id",
                "reviewer",
                "decision",
                "aaoifi_references",
                "rationale",
                "uncertainty_flags",
                "correction_type",
                "accepted_gold_case",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "review_id": "review-1",
                "mapping_id": mapping.mapping_id,
                "reviewer": "scholar-1",
                "decision": "scholar_accepted",
                "aaoifi_references": "FAS-28|SS-08",
                "rationale": "Evidence supports murabaha mapping.",
                "uncertainty_flags": "",
                "correction_type": "",
                "accepted_gold_case": "true",
            }
        )

    reviews = ScholarReviewCsvStore.import_reviews(review_path)
    registry.add_scholar_review(reviews[0])
    gold_cases = ScholarReviewCsvStore.accepted_gold_cases(registry)

    assert candidate_path.read_text(encoding="utf-8").startswith("review_id,mapping_id,operation_id")
    assert reviews[0].accepted_gold_case is True
    assert gold_cases[0]["operation_name"] == operation.operation_name
    assert gold_cases[0]["aaoifi_references"] == ["FAS-28", "SS-08"]


def test_operation_runtime_promotion_requires_accepted_scholar_gold_case():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = PublicArtifactRecord.from_mapping(
        {
            **_artifact("art-1", record.institution_id).to_dict(),
            "artifact_type": PublicArtifactType.CONTRACT.value,
            "artifact_class": ArtifactClass.TERMS_OR_CONTRACT.value,
        }
    )
    operation = OperationExtractor().extract(
        institution_id=record.institution_id,
        artifact=artifact,
        text="Murabaha terms include bank purchases and ownership transfer.",
    )
    mapping = AaoifiMappingGenerator().generate(operation)
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)
    registry.add_operation(operation)
    registry.add_machine_mapping(mapping)

    with pytest.raises(ValueError, match="scholar_accepted"):
        registry.promote_operation_to_runtime(mapping.mapping_id)

    registry.add_scholar_review(
        ScholarReviewRecord(
            review_id="review-accepted-1",
            mapping_id=mapping.mapping_id,
            reviewer="scholar-1",
            decision=ReviewCandidateStatus.SCHOLAR_ACCEPTED,
            aaoifi_references=["FAS-28", "SS-08"],
            rationale="Accepted from reviewed public evidence.",
            accepted_gold_case=True,
        )
    )

    promoted = registry.promote_operation_to_runtime(mapping.mapping_id)

    assert promoted.runtime_eligible is True
    assert promoted.promotion_stage == PromotionStage.RUNTIME_ELIGIBLE
    assert registry.operation(operation.operation_id).runtime_eligible is True


def test_engine_assessment_export_keeps_human_scholar_review_blank(tmp_path):
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = _artifact("art-1", record.institution_id)
    operation = OperationExtractor().extract(
        institution_id=record.institution_id,
        artifact=artifact,
        text="Murabaha terms include bank purchases and ownership transfer.",
    )
    mapping = AaoifiMappingGenerator().generate(operation)
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)
    registry.add_operation(operation)
    registry.add_machine_mapping(mapping)
    output = tmp_path / "engine_assessment_rows.csv"

    EngineAssessmentCsvStore.export_assessments(output, registry)

    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8")))
    assert rows[0]["financial_institution_name"] == "Faisal Islamic Bank of Egypt"
    assert rows[0]["contract_operation_name"] == operation.operation_name
    assert rows[0]["mushir_engine_status"] == "machine_proposed"
    assert rows[0]["mushir_engine_review"] == "Evidence suggests murabaha/deferred sale mechanics or asset ownership flow."
    assert rows[0]["mushir_engine_aaoifi_references"] == "FAS-28|SS-08"
    assert rows[0]["human_scholar_review"] == ""
    assert rows[0]["human_scholar_review_references"] == ""
    assert rows[0]["human_scholar_review_notes"] == ""


def test_scholar_review_lists_keep_arabic_and_english_rows_linked(tmp_path):
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        name_ar="\u0628\u0646\u0643 \u0641\u064a\u0635\u0644 \u0627\u0644\u0625\u0633\u0644\u0627\u0645\u064a \u0627\u0644\u0645\u0635\u0631\u064a",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = _artifact("art-1", record.institution_id)
    operation = OperationExtractor().extract(
        institution_id=record.institution_id,
        artifact=artifact,
        text="Murabaha terms include bank purchases and ownership transfer.",
    )
    mapping = AaoifiMappingGenerator().generate(operation)
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)
    registry.add_operation(operation)
    registry.add_machine_mapping(mapping)

    paths = ScholarReviewListCsvStore.export_lists(tmp_path, registry)

    bilingual = list(csv.DictReader(paths["bilingual"].open(newline="", encoding="utf-8")))
    english = list(csv.DictReader(paths["english"].open(newline="", encoding="utf-8")))
    arabic = list(csv.DictReader(paths["arabic"].open(newline="", encoding="utf-8")))
    assert bilingual[0]["review_item_number"] == english[0]["review_item_number"] == arabic[0]["review_item_number"]
    assert bilingual[0]["operation_id"] == english[0]["operation_id"] == arabic[0]["operation_id"]
    assert english[0]["institution_name"] == "Faisal Islamic Bank of Egypt"
    assert arabic[0]["institution_name"] == "\u0628\u0646\u0643 \u0641\u064a\u0635\u0644 \u0627\u0644\u0625\u0633\u0644\u0627\u0645\u064a \u0627\u0644\u0645\u0635\u0631\u064a"
    assert "\u0645\u0631\u0627\u0628\u062d\u0629" in arabic[0]["mushir_engine_review"]
    assert arabic[0]["human_scholar_review"] == ""
    assert arabic[0]["human_scholar_review_references"] == ""
    assert "\u0631\u0642\u0645 \u0627\u0644\u0628\u0646\u062f" in arabic[0]["matching_note"]


def test_exported_scholar_review_template_can_be_completed_and_imported(tmp_path):
    mapping = AaoifiMappingGenerator().generate(
        OperationExtractor().extract(
            institution_id="cbe-bank-faisal-islamic-bank-of-egypt",
            artifact=_artifact("art-1", "cbe-bank-faisal-islamic-bank-of-egypt"),
            text="Murabaha terms include bank purchases and ownership transfer.",
        )
    )
    candidate_path = tmp_path / "candidate_review.csv"
    ScholarReviewCsvStore.export_candidates(candidate_path, [mapping])

    rows = list(csv.DictReader(candidate_path.open(newline="", encoding="utf-8")))
    rows[0].update(
        {
            "reviewer": "scholar-1",
            "decision": "scholar_accepted",
            "aaoifi_references": "FAS-28|SS-08",
            "accepted_gold_case": "true",
        }
    )
    with candidate_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    reviews = ScholarReviewCsvStore.import_reviews(candidate_path)

    assert reviews[0].review_id == f"review-{mapping.mapping_id}"
    assert reviews[0].mapping_id == mapping.mapping_id
    assert reviews[0].accepted_gold_case is True


def test_corpus_pilot_gate_blocks_full_scrape_until_reviewed_hard_case_mix_exists():
    bank = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
        discovery_status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
        attempt_count=1,
    )
    insurer = InstitutionRegistryRecord.baseline(
        name_en="Delta Insurance",
        regulator=InstitutionRegulator.FRA,
        sector=InstitutionSector.INSURANCE,
        registry_source="FRA insurance register",
        registry_source_url="https://fra.gov.eg/",
        discovery_status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
        attempt_count=1,
    )
    hard_case = InstitutionRegistryRecord.baseline(
        name_en="Hard Case Finance",
        regulator=InstitutionRegulator.FRA,
        sector=InstitutionSector.CONSUMER_FINANCE,
        registry_source="FRA financing register",
        registry_source_url="https://fra.gov.eg/",
        discovery_status=InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
        attempt_count=3,
        gap_reason="No official public details found after bounded search.",
    )
    registry = InstitutionRegistry([bank, insurer, hard_case])
    for index, record in enumerate([bank, insurer], start=1):
        artifact = _artifact(f"art-{index}", record.institution_id)
        operation = OperationExtractor().extract(
            institution_id=record.institution_id,
            artifact=artifact,
            text="Murabaha deferred payment terms include ownership and fees.",
        )
        mapping = AaoifiMappingGenerator().generate(operation)
        registry.add_artifact(artifact)
        registry.add_operation(operation)
        registry.add_machine_mapping(mapping)
    first_mapping = registry.machine_mappings()[0]
    registry.add_scholar_review(
        ScholarReviewRecord(
            review_id="review-1",
            mapping_id=first_mapping.mapping_id,
            reviewer="scholar-1",
            decision=ReviewCandidateStatus.SCHOLAR_ACCEPTED,
            aaoifi_references=["FAS-28", "SS-08"],
            rationale="Accepted for pilot gate fixture.",
            accepted_gold_case=True,
        )
    )
    plan = CorpusPilotPlan(
        pilot_id="l6-pilot-fixture",
        institution_ids=[bank.institution_id, insurer.institution_id, hard_case.institution_id],
        includes_no_details_case=True,
    )

    report = CorpusPilotGate().evaluate(plan, registry)

    assert report.passed is True
    assert report.findings == []


def _artifact(artifact_id, institution_id):
    return PublicArtifactRecord(
        artifact_id=artifact_id,
        institution_id=institution_id,
        url=f"https://example.com/{artifact_id}",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.PRODUCT_PAGE,
        language="en",
        retrieved_at=date(2026, 5, 20),
        http_status=200,
        content_type="text/plain",
        content_hash="sha256:" + "0" * 64,
        raw_path=f"raw/{institution_id}/{artifact_id}.txt",
        text_path=f"extracted_text/{institution_id}/{artifact_id}.txt",
        extraction_status=ExtractionStatus.EXTRACTED,
        citation_anchor_strategy="line_range",
    )


def _write_minimal_xlsx(path, sheets):
    workbook_sheets = "\n".join(
        f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheets, start=1)
    )
    relationships = "\n".join(
        '<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet{index}.xml"/>'.format(index=index)
        for index, _ in enumerate(sheets, start=1)
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            "</Types>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{workbook_sheets}</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{relationships}</Relationships>",
        )
        for index, rows in enumerate(sheets.values(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))


def _sheet_xml(rows):
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            column = chr(ord("A") + column_index)
            cells.append(
                f'<c r="{column}{row_index}" t="inlineStr"><is><t>{value}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )
