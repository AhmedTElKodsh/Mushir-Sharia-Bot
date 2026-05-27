import pytest


@pytest.mark.unit
def test_ingest_selects_arabic_and_english_markdown(tmp_path):
    from scripts.ingest import detect_language, markdown_files

    en = tmp_path / "AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md"
    ar = tmp_path / "AAOIFI_Standard_28_ar_Financial_Accounting_Standard_2_8.md"
    index = tmp_path / "INDEX.md"
    unknown = tmp_path / "notes.md"
    for path in [en, ar, index, unknown]:
        path.write_text("content", encoding="utf-8")

    selected = markdown_files(tmp_path, ["en", "ar"])

    assert detect_language(en) == "en"
    assert detect_language(ar) == "ar"
    assert selected == [ar, en]


@pytest.mark.unit
def test_ingest_can_limit_to_arabic_markdown(tmp_path):
    from scripts.ingest import markdown_files

    (tmp_path / "AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md").write_text(
        "content", encoding="utf-8"
    )
    ar = tmp_path / "AAOIFI_Standard_28_ar_Financial_Accounting_Standard_2_8.md"
    ar.write_text("content", encoding="utf-8")

    assert markdown_files(tmp_path, ["ar"]) == [ar]


@pytest.mark.unit
def test_ingest_can_limit_to_candidate_standards_from_catalog(tmp_path):
    from scripts.ingest import filter_files_by_standards, load_source_catalog, markdown_files

    ss_03 = tmp_path / "AAOIFI_Standard_03_en_AAOIFI_Sharia_Standard_No._03_Procrastinating_Debtor.md"
    ss_19 = tmp_path / "AAOIFI_Standard_19_en_AAOIFI_Sharia_Standard_No._19_Loan_Qard.md"
    ss_11 = tmp_path / "AAOIFI_Standard_11_en_AAOIFI_Sharia_Standard_No._11_Istisnaa.md"
    for path in [ss_03, ss_19, ss_11]:
        path.write_text("content", encoding="utf-8")
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        f"""
records:
  - source_id: aaoifi-ss-03-en
    source_family: sharia_standard
    standard_number: SS-03
    title_en: Procrastinating Debtor
    language: en
    official_url: https://aaoifi.example/standards/ss-03
    acquired_at: 2026-05-25
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: {ss_03.name}
  - source_id: aaoifi-ss-19-en
    source_family: sharia_standard
    standard_number: SS-19
    title_en: Loan Qard
    language: en
    official_url: https://aaoifi.example/standards/ss-19
    acquired_at: 2026-05-25
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: {ss_19.name}
  - source_id: aaoifi-ss-11-en
    source_family: sharia_standard
    standard_number: SS-11
    title_en: Istisnaa
    language: en
    official_url: https://aaoifi.example/standards/ss-11
    acquired_at: 2026-05-25
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: {ss_11.name}
""",
        encoding="utf-8",
    )

    files = markdown_files(tmp_path, ["en"])
    selected = filter_files_by_standards(files, ["SS-3", "SS-19"], load_source_catalog(catalog_path))

    assert selected == [ss_03, ss_19]


@pytest.mark.unit
def test_ingest_detects_text_language_independently_from_filename():
    from scripts.ingest import detect_text_language

    arabic_text = "هذا نص عربي عن المرابحة والملكية والمخاطر. " * 20
    english_text = "This is English text about murabaha ownership and risk transfer. " * 20

    assert detect_text_language(arabic_text, fallback="en") == "ar"
    assert detect_text_language(english_text, fallback="ar") == "en"


@pytest.mark.unit
def test_ingest_uses_catalog_record_to_store_answer_admissible_metadata(tmp_path):
    from scripts.ingest import ingest_files, load_source_catalog

    md = tmp_path / "AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md"
    md.write_text("# Murabaha\n\n" + "Murabaha accounting evidence. " * 80, encoding="utf-8")
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        """
records:
  - source_id: fas-28-en
    source_family: fas
    standard_number: AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8
    title_en: Murabaha and Other Deferred Payment Sales
    language: en
    official_url: https://aaoifi.example/standards/fas-28
    acquired_at: 2026-05-24
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md
""",
        encoding="utf-8",
    )

    class FakeModel:
        def encode(self, chunks, normalize_embeddings=False):
            assert normalize_embeddings is True
            return type("Embeddings", (), {"tolist": lambda self: [[0.1, 0.2, 0.3] for _ in chunks]})()

    class FakeCollection:
        def __init__(self):
            self.metadatas = []

        def upsert(self, ids, embeddings, documents, metadatas):
            self.metadatas.extend(metadatas)

    class FakeSplitter:
        def split_text(self, text):
            return [text]

    collection = FakeCollection()
    total = ingest_files(
        [md],
        FakeModel(),
        collection,
        FakeSplitter(),
        "test-model",
        source_catalog=load_source_catalog(catalog_path),
    )

    assert total == 1
    assert collection.metadatas[0]["metadata_status"] == "cataloged"
    assert collection.metadatas[0]["source_id"] == "fas-28-en"
    assert collection.metadatas[0]["source_language"] == "en"
    assert collection.metadatas[0]["source_currentness"] == "current"
    assert collection.metadatas[0]["review_status"] == "machine_checked"
    assert collection.metadatas[0]["citation_anchor"] == "https://aaoifi.example/standards/fas-28#chunk-0000"


@pytest.mark.unit
def test_ingest_citation_anchor_uses_chunk_index_when_heading_is_not_stable(tmp_path):
    from scripts.ingest import citation_anchor_for_chunk, load_source_catalog

    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        """
records:
  - source_id: ss-05-ar
    source_family: sharia_standard
    standard_number: SS-05
    title_en: Guarantees
    language: ar
    official_url: https://aaoifi.example/standards/ss-05
    acquired_at: 2026-05-25
    extraction_method: derived_markdown
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: AAOIFI_Standard_05_ar_Test.md
""",
        encoding="utf-8",
    )
    record = load_source_catalog(catalog_path).get("ss-05-ar")

    assert citation_anchor_for_chunk(record, 12) == "https://aaoifi.example/standards/ss-05#chunk-0012"


@pytest.mark.unit
def test_ingest_matches_catalog_record_relative_to_corpus_dir(tmp_path):
    from scripts.ingest import catalog_record_for_file, load_source_catalog, unmatched_catalog_files

    corpus_dir = tmp_path / "knowledge-base"
    corpus_dir.mkdir()
    md = corpus_dir / "AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md"
    md.write_text("# Murabaha\n\nEvidence.", encoding="utf-8")
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        """
records:
  - source_id: fas-28-en
    source_family: fas
    standard_number: FAS-28
    title_en: Murabaha and Other Deferred Payment Sales
    language: en
    official_url: https://aaoifi.example/standards/fas-28
    acquired_at: 2026-05-24
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: gemini-gem-prototype/knowledge-base/AAOIFI_Standard_28_en_Financial_Accounting_Standard_2_8.md
""",
        encoding="utf-8",
    )

    catalog = load_source_catalog(catalog_path)

    assert catalog_record_for_file(catalog, md, corpus_dir=corpus_dir).source_id == "fas-28-en"
    assert unmatched_catalog_files([md], catalog, corpus_dir=corpus_dir) == []


@pytest.mark.unit
def test_ingest_cli_refuses_partially_unmatched_source_catalog(tmp_path, monkeypatch):
    import scripts.ingest as ingest

    md = tmp_path / "AAOIFI_Standard_99_en_Test.md"
    md.write_text("# Test\n\nUnmatched evidence.", encoding="utf-8")
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        """
records:
  - source_id: fas-28-en
    source_family: fas
    standard_number: FAS-28
    title_en: Murabaha and Other Deferred Payment Sales
    language: en
    official_url: https://aaoifi.example/standards/fas-28
    acquired_at: 2026-05-24
    extraction_method: fixture
    source_type: derived_markdown
    currentness: current
    review_status: machine_checked
    source_confidence: derived_from_official
    derived_path: AAOIFI_Standard_28_en.md
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest.py",
            "--corpus-dir",
            str(tmp_path),
            "--languages",
            "en",
            "--source-catalog",
            str(catalog_path),
        ],
    )
    monkeypatch.setattr(
        ingest,
        "SentenceTransformer",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("model should not load")),
    )

    with pytest.raises(SystemExit, match="did not match all selected markdown files"):
        ingest.main()


@pytest.mark.unit
def test_ingest_keeps_uncataloged_chunks_quarantined(tmp_path):
    from scripts.ingest import ingest_files

    md = tmp_path / "AAOIFI_Standard_99_en_Test.md"
    md.write_text("# Unknown\n\n" + "Uncataloged evidence. " * 80, encoding="utf-8")

    class FakeModel:
        def encode(self, chunks, normalize_embeddings=False):
            return type("Embeddings", (), {"tolist": lambda self: [[0.1] for _ in chunks]})()

    class FakeCollection:
        def __init__(self):
            self.metadatas = []

        def upsert(self, ids, embeddings, documents, metadatas):
            self.metadatas.extend(metadatas)

    class FakeSplitter:
        def split_text(self, text):
            return [text]

    collection = FakeCollection()
    ingest_files([md], FakeModel(), collection, FakeSplitter(), "test-model")

    assert collection.metadatas[0]["metadata_status"] == "quarantined_missing_catalog"


@pytest.mark.unit
def test_ingest_cli_refuses_uncataloged_rebuild_before_loading_model(tmp_path, monkeypatch):
    import scripts.ingest as ingest

    md = tmp_path / "AAOIFI_Standard_28_en_Test.md"
    md.write_text("# Test\n\nMurabaha evidence.", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest.py",
            "--corpus-dir",
            str(tmp_path),
            "--languages",
            "en",
            "--reset",
        ],
    )
    monkeypatch.setattr(
        ingest,
        "SentenceTransformer",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("model should not load")),
    )

    with pytest.raises(SystemExit, match="Refusing to ingest without --source-catalog"):
        ingest.main()
