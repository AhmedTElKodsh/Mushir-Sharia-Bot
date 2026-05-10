import json
import sqlite3
import os
from typing import Optional, List, Dict
from src.models.document import AAOIFIDocument
from datetime import datetime

DEFAULT_DB_PATH = "./data/documents.db"

class DocumentStore:
    """SQLite-based document storage for MVP."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aaoifi_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    standard_number TEXT,
                    standard_type TEXT DEFAULT 'FAS',
                    source_url TEXT,
                    acquired_at TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    status TEXT DEFAULT 'active',
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_document_id ON aaoifi_documents(document_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON aaoifi_documents(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_standard_number ON aaoifi_documents(standard_number)")
            conn.commit()

    def store_document(self, doc: AAOIFIDocument) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO aaoifi_documents
                (document_id, title, content, standard_number, standard_type, source_url, acquired_at, version, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.document_id,
                doc.title,
                doc.content,
                doc.standard_number,
                doc.standard_type,
                doc.source_url,
                doc.acquired_at.isoformat(),
                doc.version,
                doc.status,
                json.dumps(doc.metadata),
            ))

    def _load_metadata(self, value: Optional[str]) -> Dict:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def get_document(self, document_id: str) -> Optional[AAOIFIDocument]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aaoifi_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if row:
                return AAOIFIDocument(
                    document_id=row["document_id"],
                    title=row["title"],
                    content=row["content"],
                    standard_number=row["standard_number"],
                    standard_type=row["standard_type"],
                    source_url=row["source_url"],
                    acquired_at=datetime.fromisoformat(row["acquired_at"]),
                    version=row["version"],
                    status=row["status"],
                    metadata=self._load_metadata(row["metadata"]),
                )
        return None

    def get_all_documents(self) -> List[AAOIFIDocument]:
        docs = []
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM aaoifi_documents WHERE status = 'active'").fetchall()
            for row in rows:
                docs.append(AAOIFIDocument(
                    document_id=row["document_id"],
                    title=row["title"],
                    content=row["content"],
                    standard_number=row["standard_number"],
                    standard_type=row["standard_type"],
                    source_url=row["source_url"],
                    acquired_at=datetime.fromisoformat(row["acquired_at"]),
                    version=row["version"],
                    status=row["status"],
                    metadata=self._load_metadata(row["metadata"]),
                ))
        return docs

    def delete_document(self, document_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE aaoifi_documents SET status = 'deleted' WHERE document_id = ?", (document_id,))
            conn.commit()
