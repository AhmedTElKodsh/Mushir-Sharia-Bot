from datetime import date

import pytest

from src.governance import (
    AccessControlDecision,
    AccessControlSignal,
    AccessDecisionStatus,
    ComplianceRiskLabel,
    CorpusPilotPlan,
    DiscoveryEvidenceType,
    DiscoveryStopReason,
    DocumentVersionRecord,
    ExtractionStatus,
    InstitutionDiscoveryStatus,
    InstitutionRegulator,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionSector,
    MachineAaoifiMappingCandidate,
    OfficialSiteDiscoveryAttempt,
    OfficialSiteDiscoveryResult,
    OperationCatalogRecord,
    OperationEvidenceField,
    OperationEvidenceSpan,
    PublicArtifactAuthorityRank,
    PublicArtifactRecord,
    PublicArtifactType,
    ReviewCandidateStatus,
    ScholarReviewRecord,
    UserFactOverrideDecision,
    ParentChildChunkMetadataBuilder,
    RouterSeedRecord,
    RouterSeedStatus,
    SourceCatalog,
    SourceCatalogRecord,
    SourceConfidence,
    SourceCurrentness,
    SourceRelationshipRecord,
    SourceRelationshipType,
    SourceReviewStatus,
    SourceType,
    TerminologySeedEvaluation,
    TerminologySeedSource,
    TerminologySeedStatus,
    default_concept_map,
    default_candidate_supersession_relationships,
    default_router_seed_registry,
    stable_institution_id,
)
from src.models.commercial import ContractFamily, QuestionType, SourceFamily


pytestmark = pytest.mark.service


def _fas_28_record() -> SourceCatalogRecord:
    return SourceCatalogRecord(
        source_id="aaoifi-fas-28-en",
        source_family=SourceFamily.FAS,
        standard_number="FAS-28",
        title_en="Murabaha and Other Deferred Payment Sales",
        language="en",
        official_url="https://aaoifi.com/accounting-standards-2/?lang=en",
        acquired_at=date(2026, 5, 19),
        extraction_method="pdf_conversion",
        source_type=SourceType.DERIVED_MARKDOWN,
        currentness=SourceCurrentness.CURRENT,
        review_status=SourceReviewStatus.MACHINE_CHECKED,
        source_confidence=SourceConfidence.DERIVED_FROM_OFFICIAL,
        derived_path="gemini-gem-prototype/knowledge-base/AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md",
    )


def test_catalog_record_exports_answer_admissible_chunk_metadata():
    record = _fas_28_record()

    metadata = record.to_chunk_metadata("AAOIFI_Standard_28_en.md", 0, 4)

    assert record.is_answer_admissible is True
    assert metadata["source_id"] == "aaoifi-fas-28-en"
    assert metadata["source_family"] == "fas"
    assert metadata["source_currentness"] == "current"
    assert metadata["official_url"].startswith("https://aaoifi.com/")


def test_catalog_validation_rejects_missing_unknown_or_unverified_sources():
    unverified = SourceCatalogRecord(
        source_id="aaoifi-fas-99-en",
        source_family=SourceFamily.FAS,
        standard_number="FAS-99",
        title_en="Unverified",
        language="en",
        official_url="https://aaoifi.com/accounting-standards-2/?lang=en",
        acquired_at=date(2026, 5, 19),
        extraction_method="manual",
        source_type=SourceType.MANUAL_TEXT,
    )
    catalog = SourceCatalog([unverified])

    assert catalog.validate_chunk_metadata({}) == ["missing source_id"]
    assert catalog.validate_chunk_metadata({"source_id": "missing"}) == ["unknown source_id: missing"]
    assert catalog.validate_chunk_metadata(
        {
            "source_id": "aaoifi-fas-99-en",
            "source_family": "fas",
            "standard_number": "FAS-99",
            "language": "en",
            "source_currentness": "unverified",
        }
    ) == ["source is not answer-admissible"]


def test_document_versions_link_source_records_to_corpus_versions():
    record = _fas_28_record()
    version = DocumentVersionRecord(
        document_id="aaoifi-fas-28-en-v2026-05-19",
        source_id=record.source_id,
        corpus_version="corpus-2026-05-19",
        index_version="chroma-multilingual-2026-05-19",
        extraction_hash="sha256:abc123",
        version_status=SourceCurrentness.CURRENT,
        acquired_at=date(2026, 5, 19),
        extraction_method="pdf_conversion",
    )
    catalog = SourceCatalog([record], document_versions=[version])

    assert catalog.document_version(version.document_id) == version
    assert catalog.document_versions_for_source(record.source_id) == [version]


def test_document_versions_reject_unknown_sources():
    with pytest.raises(KeyError, match="unknown source_id"):
        SourceCatalog(
            [],
            document_versions=[
                DocumentVersionRecord(
                    document_id="orphan",
                    source_id="missing-source",
                    corpus_version="corpus-2026-05-19",
                    index_version="index-2026-05-19",
                    extraction_hash="sha256:abc123",
                    version_status=SourceCurrentness.CURRENT,
                    acquired_at=date(2026, 5, 19),
                    extraction_method="manual",
                )
            ],
        )


def test_source_relationships_capture_supersession_edges():
    old = SourceCatalogRecord(
        source_id="aaoifi-fas-02-en",
        source_family=SourceFamily.FAS,
        standard_number="FAS-02",
        title_en="Old Murabaha Standard",
        language="en",
        official_url="https://aaoifi.com/accounting-standards-2/?lang=en",
        acquired_at=date(2026, 5, 19),
        extraction_method="manual",
        source_type=SourceType.MANUAL_TEXT,
        currentness=SourceCurrentness.SUPERSEDED,
        superseded_by=["aaoifi-fas-28-en"],
    )
    current = _fas_28_record()
    edge = SourceRelationshipRecord(
        relationship_id="fas-02-superseded-by-fas-28",
        source_id=old.source_id,
        related_source_id=current.source_id,
        relationship_type=SourceRelationshipType.SUPERSEDES,
        review_status=SourceReviewStatus.UNREVIEWED,
        notes="Candidate edge from 2026-05-19 research report; requires catalog verification.",
    )
    catalog = SourceCatalog([old, current], relationships=[edge])

    assert catalog.relationships_for_source(old.source_id) == [edge]
    assert catalog.relationships_for_source(current.source_id) == []


def test_source_relationships_reject_unknown_sources():
    with pytest.raises(KeyError, match="unknown source_id"):
        SourceCatalog(
            [_fas_28_record()],
            relationships=[
                SourceRelationshipRecord(
                    relationship_id="bad-edge",
                    source_id="missing-source",
                    related_source_id="aaoifi-fas-28-en",
                    relationship_type=SourceRelationshipType.CLARIFIES,
                )
            ],
        )


def test_default_candidate_supersession_edges_are_unverified_review_items():
    edges = default_candidate_supersession_relationships()

    assert edges[0].relationship_type == SourceRelationshipType.SUPERSEDES
    assert all(edge.review_status == SourceReviewStatus.UNREVIEWED for edge in edges)
    assert "catalog verification required" in edges[0].notes


def test_default_router_seeds_store_first_release_routes_as_reviewable_data():
    registry = default_router_seed_registry()

    murabaha = registry.match("How should murabaha profit be recognized?")
    zakah = registry.match("\u0645\u0627 \u0645\u0639\u064a\u0627\u0631 \u0627\u0644\u0632\u0643\u0627\u0629\u061f")
    salam = registry.match("parallel salam accounting")
    ijarah = registry.match("\u0627\u0644\u0625\u062c\u0627\u0631\u0629")
    sukuk = registry.match("shares and similar instruments")

    assert murabaha is not None
    assert murabaha.route_id == "murabaha-accounting"
    assert murabaha.status == RouterSeedStatus.UNVERIFIED
    assert murabaha.candidate_standards == ["FAS-28"]
    assert zakah is not None
    assert "FAS-39" in zakah.candidate_standards
    assert salam is not None
    assert ijarah is not None
    assert sukuk is not None
    assert murabaha.allows_retrieval is True


def test_router_seed_registry_filters_verified_routes_for_retrieval():
    verified = RouterSeedRecord(
        route_id="verified-route",
        canonical_concept="murabaha",
        contract_family=ContractFamily.MURABAHA,
        question_types=[QuestionType.ACCOUNTING],
        source_families=[SourceFamily.FAS],
        candidate_standards=["FAS-28"],
        terms_en=["murabaha"],
        status=RouterSeedStatus.CATALOG_VERIFIED,
    )
    unverified = RouterSeedRecord(
        route_id="unverified-route",
        canonical_concept="ijarah",
        contract_family=ContractFamily.IJARAH,
        question_types=[QuestionType.ACCOUNTING],
        source_families=[SourceFamily.FAS],
        candidate_standards=["FAS-32"],
        terms_en=["ijarah"],
    )
    registry = default_router_seed_registry([verified, unverified])

    assert registry.verified_routes_for(SourceFamily.FAS) == [verified]


def test_parent_child_chunk_metadata_marks_uncataloged_chunks_quarantined():
    builder = ParentChildChunkMetadataBuilder(
        source_file="AAOIFI_Standard_28_en.md",
        standard_number="FAS-28",
        language="en",
        embedding_model="test-model",
        embedding_normalized=True,
        total_chunks=2,
    )

    metadata = builder.child_metadata(
        chunk_index=0,
        section_path=["FAS-28", "Recognition"],
        operation_tags=["murabaha"],
        citation_anchor="Recognition",
    )

    assert metadata["parent_chunk_id"] == "AAOIFI_Standard_28_en:FAS-28-Recognition"
    assert metadata["chunk_idx"] == 0
    assert metadata["section_path"] == "FAS-28 > Recognition"
    assert metadata["operation_tags"] == "murabaha"
    assert metadata["citation_anchor"] == "Recognition"
    assert metadata["metadata_status"] == "quarantined_missing_catalog"
    assert metadata["source_id"] == ""


def test_parent_child_chunk_metadata_uses_catalog_record_when_available():
    record = _fas_28_record()
    builder = ParentChildChunkMetadataBuilder(
        source_file="AAOIFI_Standard_28_en.md",
        standard_number="FAS-28",
        language="en",
        embedding_model="test-model",
        embedding_normalized=True,
        total_chunks=1,
        catalog_record=record,
        document_version_id="aaoifi-fas-28-en-v2026-05-19",
    )

    metadata = builder.child_metadata(chunk_index=0, section_path=["FAS-28"])

    assert metadata["source_id"] == record.source_id
    assert metadata["document_version_id"] == "aaoifi-fas-28-en-v2026-05-19"
    assert metadata["source_currentness"] == "current"
    assert metadata["metadata_status"] == "cataloged"


def test_catalog_finds_records_by_derived_path_and_filters_admissible_family():
    record = _fas_28_record()
    catalog = SourceCatalog([record])

    assert catalog.find_by_path(record.derived_path).source_id == record.source_id
    assert catalog.admissible_records(SourceFamily.FAS) == [record]
    assert catalog.admissible_records(SourceFamily.SHARIA_STANDARD) == []


def test_superseded_records_must_name_replacement():
    with pytest.raises(ValueError, match="superseded_by"):
        SourceCatalogRecord(
            source_id="aaoifi-fas-old-en",
            source_family=SourceFamily.FAS,
            standard_number="FAS-OLD",
            title_en="Old standard",
            language="en",
            official_url="https://aaoifi.com/accounting-standards-2/?lang=en",
            acquired_at=date(2026, 5, 19),
            extraction_method="manual",
            source_type=SourceType.MANUAL_TEXT,
            currentness=SourceCurrentness.SUPERSEDED,
        )


def test_default_concept_map_matches_bilingual_and_colloquial_murabaha_terms():
    concepts = default_concept_map()

    murabaha = concepts.primary_match(
        "\u0639\u0627\u064a\u0632 \u062a\u0642\u0633\u064a\u0637 "
        "\u0633\u064a\u0627\u0631\u0629 \u0639\u0644\u0649 "
        "\u0645\u0631\u0627\u0628\u062d\u0647"
    )

    assert murabaha is not None
    assert murabaha.concept_id == "murabaha"
    assert murabaha.contract_family == ContractFamily.MURABAHA
    assert SourceFamily.FAS in murabaha.candidate_source_families
    assert SourceFamily.SHARIA_STANDARD in murabaha.candidate_source_families


def test_default_concept_map_routes_late_payment_to_sharia_family():
    families = default_concept_map().source_families_for("late payment penalty in murabaha")

    assert SourceFamily.SHARIA_STANDARD in families


def test_external_terminology_requires_review_before_concept_map_adoption():
    pending = TerminologySeedEvaluation(
        term="asset backed sukuk",
        source=TerminologySeedSource.FIBO,
        proposed_concept_id="sukuk",
        status=TerminologySeedStatus.PENDING_REVIEW,
        reviewer="",
        rationale="",
    )
    accepted = TerminologySeedEvaluation(
        term="asset backed sukuk",
        source=TerminologySeedSource.FIBO,
        proposed_concept_id="sukuk",
        status=TerminologySeedStatus.REVIEWED_ACCEPTED,
        reviewer="reviewer-1",
        rationale="Term aligns with reviewed Mushir sukuk concept.",
    )

    assert pending.can_enter_concept_map is False
    assert accepted.can_enter_concept_map is True


def test_institution_registry_creates_stable_baseline_ids_and_filters_records():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="Egypt financial institutions refresh workbook",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
        baseline_inputs=["Egypt_Financial_Institutions_COMPLETE.xlsx"],
    )
    registry = InstitutionRegistry([record])

    assert record.institution_id == "cbe-bank-faisal-islamic-bank-of-egypt"
    assert registry.get(record.institution_id) == record
    assert registry.by_sector(InstitutionSector.BANK) == [record]
    assert registry.by_regulator(InstitutionRegulator.CBE) == [record]
    assert record.to_dict()["refresh_status"] == "baseline_unverified"


def test_institution_registry_rejects_rows_missing_regulator_or_source_provenance():
    with pytest.raises(ValueError, match="regulator provenance"):
        InstitutionRegistryRecord.baseline(
            name_en="Unknown Institution",
            regulator=InstitutionRegulator.UNKNOWN,
            sector=InstitutionSector.BANK,
            registry_source="Egypt financial institutions refresh workbook",
            registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
        )

    with pytest.raises(ValueError, match="registry_source"):
        InstitutionRegistryRecord(
            institution_id="cbe-bank-no-source",
            name_en="No Source Bank",
            regulator=InstitutionRegulator.CBE,
            sector=InstitutionSector.BANK,
            registry_source="",
            registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
        )


def test_institution_registry_requires_gap_reason_for_bounded_discovery_gaps():
    with pytest.raises(ValueError, match="gap_reason"):
        InstitutionRegistryRecord.baseline(
            name_en="Hard Case Finance",
            regulator=InstitutionRegulator.FRA,
            sector=InstitutionSector.CONSUMER_FINANCE,
            registry_source="FRA financing register",
            registry_source_url="https://fra.gov.eg/",
            discovery_status=InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
            attempt_count=2,
        )

    record = InstitutionRegistryRecord.baseline(
        name_en="Hard Case Finance",
        regulator=InstitutionRegulator.FRA,
        sector=InstitutionSector.CONSUMER_FINANCE,
        registry_source="FRA financing register",
        registry_source_url="https://fra.gov.eg/",
        discovery_status=InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA,
        attempt_count=2,
        gap_reason="No official tariff or contract details found after bounded search.",
    )

    assert record.discovery_status == InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA
    assert stable_institution_id(
        "Hard Case Finance",
        InstitutionRegulator.FRA,
        InstitutionSector.CONSUMER_FINANCE,
    ) == record.institution_id


def test_official_site_discovery_result_confirms_best_evidence_and_updates_registry():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    attempts = [
        OfficialSiteDiscoveryAttempt(
            attempt_number=1,
            evidence_type=DiscoveryEvidenceType.SEARCH_RESULT,
            evidence_url="https://example.com/faisal-bank",
            confidence=0.35,
            status=InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
            checked_at=date(2026, 5, 20),
            notes="Search result is not enough for authority.",
        ),
        OfficialSiteDiscoveryAttempt(
            attempt_number=2,
            evidence_type=DiscoveryEvidenceType.REGULATOR_LINK,
            evidence_url="https://www.faisalbank.com.eg/",
            confidence=0.95,
            status=InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED,
            checked_at=date(2026, 5, 20),
            stop_reason=DiscoveryStopReason.CONFIRMED_OFFICIAL_SITE,
        ),
    ]

    result = OfficialSiteDiscoveryResult.from_attempts(record.institution_id, attempts)
    registry = InstitutionRegistry([record]).with_discovery_result(result)
    updated = registry.get(record.institution_id)

    assert result.selected_url == "https://www.faisalbank.com.eg/"
    assert result.confidence == 0.95
    assert updated.discovery_status == InstitutionDiscoveryStatus.OFFICIAL_SITE_CONFIRMED
    assert updated.official_website == "https://www.faisalbank.com.eg/"
    assert updated.attempt_count == 2
    assert updated.gap_reason == ""


def test_official_site_discovery_result_preserves_gap_reason_for_blocked_sources():
    attempt = OfficialSiteDiscoveryAttempt(
        attempt_number=1,
        evidence_type=DiscoveryEvidenceType.OFFICIAL_WEBSITE,
        evidence_url="https://blocked.example.com/",
        confidence=0.8,
        status=InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
        checked_at=date(2026, 5, 20),
        stop_reason=DiscoveryStopReason.BLOCKED_BY_SECURITY,
        notes="Site blocks automated access; do not bypass.",
    )

    result = OfficialSiteDiscoveryResult.from_attempts("fra-consumer-finance-blocked", [attempt])

    assert result.selected_url is None
    assert result.stop_reason == DiscoveryStopReason.BLOCKED_BY_SECURITY
    assert result.gap_reason == "Site blocks automated access; do not bypass."


def test_official_site_discovery_attempts_must_be_ordered_and_contiguous():
    attempts = [
        OfficialSiteDiscoveryAttempt(
            attempt_number=2,
            evidence_type=DiscoveryEvidenceType.SEARCH_RESULT,
            evidence_url="https://example.com/",
            confidence=0.1,
            status=InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
            checked_at=date(2026, 5, 20),
            notes="No authoritative source found.",
        )
    ]

    with pytest.raises(ValueError, match="ordered and contiguous"):
        OfficialSiteDiscoveryResult.from_attempts("missing-order", attempts)


def test_public_artifact_record_preserves_capture_metadata_and_filters_evidence():
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = PublicArtifactRecord(
        artifact_id="faisal-tariff-2026-05-20",
        institution_id=record.institution_id,
        url="https://www.faisalbank.com.eg/tariffs.pdf",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.TARIFF,
        language="en",
        retrieved_at=date(2026, 5, 20),
        http_status=200,
        content_type="application/pdf",
        content_hash="sha256:abc123",
        raw_path="artifacts/l6_scrape/raw/faisal-tariff.pdf",
        text_path="artifacts/l6_scrape/text/faisal-tariff.txt",
        extraction_status=ExtractionStatus.EXTRACTED,
        citation_anchor_strategy="page_number",
    )
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)

    assert registry.artifacts_for(record.institution_id) == [artifact]
    assert registry.evidence_artifacts_for(record.institution_id) == [artifact]
    assert artifact.to_dict()["authority_rank"] == "official_institution"


def test_public_artifact_extraction_requires_raw_and_text_paths():
    with pytest.raises(ValueError, match="raw_path and text_path"):
        PublicArtifactRecord(
            artifact_id="missing-paths",
            institution_id="cbe-bank-faisal",
            url="https://www.faisalbank.com.eg/tariffs.pdf",
            authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
            artifact_type=PublicArtifactType.TARIFF,
            language="en",
            retrieved_at=date(2026, 5, 20),
            http_status=200,
            content_type="application/pdf",
            content_hash="sha256:abc123",
            extraction_status=ExtractionStatus.EXTRACTED,
            citation_anchor_strategy="page_number",
        )


def test_third_party_artifacts_are_discovery_only_not_compliance_evidence():
    with pytest.raises(ValueError, match="third-party discovery"):
        PublicArtifactRecord(
            artifact_id="third-party-result",
            institution_id="cbe-bank-faisal",
            url="https://example.com/faisal-bank",
            authority_rank=PublicArtifactAuthorityRank.THIRD_PARTY_DISCOVERY_ONLY,
            artifact_type=PublicArtifactType.PRODUCT_PAGE,
            language="en",
            retrieved_at=date(2026, 5, 20),
            http_status=200,
            content_type="text/html",
            content_hash="sha256:abc123",
            raw_path="artifacts/l6_scrape/raw/third-party.html",
            text_path="artifacts/l6_scrape/text/third-party.txt",
            extraction_status=ExtractionStatus.EXTRACTED,
            citation_anchor_strategy="html_heading",
        )


def test_access_control_decision_blocks_robots_terms_and_security_signals():
    robots = AccessControlDecision.evaluate(
        url="https://www.bank.example/private/tariffs.pdf",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.ROBOTS_DISALLOW],
        reason="robots.txt disallows this path.",
    )
    terms = AccessControlDecision.evaluate(
        url="https://www.bank.example/terms-blocked.pdf",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.TERMS_DISALLOW],
        reason="Terms prohibit automated collection.",
    )
    captcha = AccessControlDecision.evaluate(
        url="https://www.bank.example/captcha",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.CAPTCHA],
        reason="CAPTCHA detected; do not bypass access controls.",
    )

    assert robots.status == AccessDecisionStatus.BLOCKED_BY_ROBOTS
    assert terms.status == AccessDecisionStatus.BLOCKED_BY_TERMS
    assert captcha.status == AccessDecisionStatus.BLOCKED_BY_SECURITY
    assert robots.allows_fetch is False
    assert robots.to_discovery_status() == InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY
    assert robots.to_extraction_status() == ExtractionStatus.BLOCKED_BY_SECURITY


def test_access_control_decision_maps_login_paywall_and_rate_limit_to_gap_statuses():
    login = AccessControlDecision.evaluate(
        url="https://www.bank.example/customer-contract.pdf",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.LOGIN_REQUIRED],
        reason="Document requires a customer login.",
    )
    paywall = AccessControlDecision.evaluate(
        url="https://www.bank.example/report.pdf",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.PAYWALL],
        reason="Document is not publicly accessible.",
    )
    rate_limited = AccessControlDecision.evaluate(
        url="https://www.bank.example/tariffs.pdf",
        checked_at=date(2026, 5, 20),
        signals=[AccessControlSignal.RATE_LIMITED],
        retry_after_seconds=3600,
        reason="Server returned a retry-after window.",
    )

    assert login.to_discovery_status() == InstitutionDiscoveryStatus.REQUIRES_LOGIN
    assert login.to_extraction_status() == ExtractionStatus.REQUIRES_LOGIN
    assert paywall.to_discovery_status() == InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC
    assert paywall.to_extraction_status() == ExtractionStatus.NOT_PUBLIC
    assert rate_limited.status == AccessDecisionStatus.RATE_LIMITED
    assert rate_limited.to_dict()["retry_after_seconds"] == 3600


def test_access_control_decision_allows_fetch_only_without_blocking_signals():
    allowed = AccessControlDecision.evaluate(
        url="https://www.bank.example/public/tariffs.pdf",
        checked_at=date(2026, 5, 20),
    )

    assert allowed.allows_fetch is True
    assert allowed.status == AccessDecisionStatus.ALLOWED
    assert allowed.to_extraction_status() == ExtractionStatus.NOT_STARTED

    with pytest.raises(ValueError, match="reason is required"):
        AccessControlDecision.evaluate(
            url="https://www.bank.example/login",
            checked_at=date(2026, 5, 20),
            signals=[AccessControlSignal.LOGIN_REQUIRED],
        )


def _institution_with_artifacts() -> tuple[InstitutionRegistry, InstitutionRegistryRecord, PublicArtifactRecord]:
    record = InstitutionRegistryRecord.baseline(
        name_en="Faisal Islamic Bank of Egypt",
        regulator=InstitutionRegulator.CBE,
        sector=InstitutionSector.BANK,
        registry_source="CBE bank register",
        registry_source_url="https://www.cbe.org.eg/en/banking-supervision",
    )
    artifact = PublicArtifactRecord(
        artifact_id="faisal-contract-2026-05-20",
        institution_id=record.institution_id,
        url="https://www.faisalbank.com.eg/contracts/murabaha.pdf",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.CONTRACT,
        language="en",
        retrieved_at=date(2026, 5, 20),
        http_status=200,
        content_type="application/pdf",
        content_hash="sha256:contract",
        raw_path="artifacts/l6_scrape/raw/faisal-contract.pdf",
        text_path="artifacts/l6_scrape/text/faisal-contract.txt",
        extraction_status=ExtractionStatus.EXTRACTED,
        citation_anchor_strategy="page_number",
    )
    registry = InstitutionRegistry([record])
    registry.add_artifact(artifact)
    return registry, record, artifact


def test_prioritized_artifacts_put_contract_economic_substance_before_product_pages():
    registry, record, _ = _institution_with_artifacts()
    product_page = PublicArtifactRecord(
        artifact_id="faisal-product-page",
        institution_id=record.institution_id,
        url="https://www.faisalbank.com.eg/products/car-finance",
        authority_rank=PublicArtifactAuthorityRank.OFFICIAL_INSTITUTION,
        artifact_type=PublicArtifactType.PRODUCT_PAGE,
        language="en",
        retrieved_at=date(2026, 5, 20),
        http_status=200,
        content_type="text/html",
        content_hash="sha256:page",
        raw_path="artifacts/l6_scrape/raw/product.html",
        text_path="artifacts/l6_scrape/text/product.txt",
        extraction_status=ExtractionStatus.EXTRACTED,
        citation_anchor_strategy="html_heading",
    )
    registry.add_artifact(product_page)

    ordered = registry.prioritized_artifacts_for(record.institution_id)

    assert ordered[0].artifact_type == PublicArtifactType.CONTRACT
    assert ordered[-1].artifact_type == PublicArtifactType.PRODUCT_PAGE


def test_operations_catalog_preserves_required_economic_evidence_spans():
    registry, record, artifact = _institution_with_artifacts()
    operation = OperationCatalogRecord(
        operation_id="faisal-car-murabaha",
        institution_id=record.institution_id,
        operation_name="Car murabaha",
        artifact_ids=[artifact.artifact_id],
        evidence_spans=[
            OperationEvidenceSpan(
                artifact_id=artifact.artifact_id,
                field=OperationEvidenceField.FEES,
                text="Administrative fee is disclosed in the tariff.",
                page=2,
                citation_anchor="p2-fees",
            ),
            OperationEvidenceSpan(
                artifact_id=artifact.artifact_id,
                field=OperationEvidenceField.LATE_PAYMENT_CLAUSES,
                text="Late-payment clause sends penalty amounts to charity.",
                page=4,
                citation_anchor="p4-late-payment",
            ),
            OperationEvidenceSpan(
                artifact_id=artifact.artifact_id,
                field=OperationEvidenceField.OWNERSHIP_OR_ASSET_FLOW,
                text="The bank purchases the vehicle before selling it to the customer.",
                page=1,
                citation_anchor="p1-asset-flow",
            ),
        ],
    )
    registry.add_operation(operation)

    assert registry.operations_for(record.institution_id) == [operation]
    assert OperationEvidenceField.FEES in operation.fields_present()
    assert OperationEvidenceField.LATE_PAYMENT_CLAUSES in operation.fields_present()


def test_machine_aaoifi_mapping_stays_proposed_until_scholar_review_accepts_gold_case():
    registry, record, artifact = _institution_with_artifacts()
    operation = OperationCatalogRecord(
        operation_id="faisal-car-murabaha",
        institution_id=record.institution_id,
        operation_name="Car murabaha",
        artifact_ids=[artifact.artifact_id],
    )
    registry.add_operation(operation)
    mapping = MachineAaoifiMappingCandidate(
        mapping_id="map-faisal-car-murabaha",
        operation_id=operation.operation_id,
        candidate_standards=["FAS-28", "SS-08"],
        risk_label=ComplianceRiskLabel.MEDIUM,
        rationale="Murabaha product with late-payment and asset-flow evidence.",
    )
    registry.add_machine_mapping(mapping)
    review = ScholarReviewRecord(
        review_id="review-map-faisal-car-murabaha",
        mapping_id=mapping.mapping_id,
        reviewer="reviewer-1",
        decision=ReviewCandidateStatus.SCHOLAR_ACCEPTED,
        aaoifi_references=["SS-08", "FAS-28"],
        rationale="Evidence supports using the row as a supervised gold case.",
        accepted_gold_case=True,
    )
    registry.add_scholar_review(review)

    assert mapping.status == ReviewCandidateStatus.MACHINE_PROPOSED
    assert registry.accepted_gold_reviews() == [review]


def test_user_fact_override_prioritizes_user_details_and_flags_public_conflicts():
    decision = UserFactOverrideDecision(
        operation_id="faisal-car-murabaha",
        user_facts={"late_payment_clause": "bank keeps the penalty"},
        public_conflict_flags=["public artifact says charity beneficiary"],
    )

    assert decision.should_prioritize_user_facts is True
    assert decision.should_flag_public_data is True


def test_corpus_pilot_requires_mixed_sample_and_no_details_case():
    plan = CorpusPilotPlan(
        pilot_id="egypt-l6-pilot-1",
        institution_ids=["cbe-bank-a", "fra-insurer-b", "fra-consumer-finance-c"],
        includes_no_details_case=True,
    )

    assert plan.institution_ids[0] == "cbe-bank-a"

    with pytest.raises(ValueError, match="no-details-found"):
        CorpusPilotPlan(
            pilot_id="bad-pilot",
            institution_ids=["cbe-bank-a", "fra-insurer-b", "fra-consumer-finance-c"],
            includes_no_details_case=False,
        )
