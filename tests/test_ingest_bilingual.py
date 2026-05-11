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
def test_ingest_detects_text_language_independently_from_filename():
    from scripts.ingest import detect_text_language

    arabic_text = "هذا نص عربي عن المرابحة والملكية والمخاطر. " * 20
    english_text = "This is English text about murabaha ownership and risk transfer. " * 20

    assert detect_text_language(arabic_text, fallback="en") == "ar"
    assert detect_text_language(english_text, fallback="ar") == "en"
