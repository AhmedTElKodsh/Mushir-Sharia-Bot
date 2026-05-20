from datetime import date

import pytest

from src.governance import (
    DocumentVersionRecord,
    InstitutionDiscoveryStatus,
    InstitutionRegulator,
    InstitutionRegistry,
    InstitutionRegistryRecord,
    InstitutionSector,
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
    default_concept_map,
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


def test_default_router_seeds_store_first_release_routes_as_reviewable_data():
    registry = default_router_seed_registry()

    murabaha = registry.match("How should murabaha profit be recognized?")
    zakah = registry.match("\u0645\u0627 \u0645\u0639\u064a\u0627\u0631 \u0627\u0644\u0632\u0643\u0627\u0629\u061f")

    assert murabaha is not None
    assert murabaha.route_id == "murabaha-accounting"
    assert murabaha.status == RouterSeedStatus.UNVERIFIED
    assert murabaha.candidate_standards == ["FAS-28"]
    assert zakah is not None
    assert "FAS-39" in zakah.candidate_standards


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
