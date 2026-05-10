from src.acquisition.storage import DocumentStore
from src.models.document import AAOIFIDocument

import pytest

pytestmark = pytest.mark.unit


def test_document_store_round_trips_metadata_without_eval(tmp_path):
    store = DocumentStore(str(tmp_path / "documents.db"))
    doc = AAOIFIDocument(
        document_id="fas-1",
        title="FAS 1",
        content="A document with enough content for storage.",
        metadata={"language": "en", "pages": 12},
    )

    store.store_document(doc)
    stored = store.get_document("fas-1")

    assert stored.metadata == {"language": "en", "pages": 12}


def test_document_store_rejects_non_json_metadata_payload(tmp_path):
    store = DocumentStore(str(tmp_path / "documents.db"))
    with store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO aaoifi_documents
            (document_id, title, content, acquired_at, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "unsafe",
                "Unsafe",
                "Content",
                "2026-05-10T08:00:00+00:00",
                "__import__('os').system('echo unsafe')",
            ),
        )

    stored = store.get_document("unsafe")

    assert stored.metadata == {}
