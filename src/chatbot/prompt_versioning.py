import sqlite3
from typing import Optional, List, Dict
from datetime import UTC, datetime
from src.config.logging_config import setup_logging

logger = setup_logging()

class SystemPromptVersionManager:
    """Manage system prompt versions."""

    def __init__(self, db_path: str = "./data/documents.db"):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    rationale TEXT,
                    is_active BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()

    def save_version(self, version: str, prompt_text: str, created_by: str = "system", rationale: str = "") -> int:
        with self._get_connection() as conn:
            # Deactivate previous active
            conn.execute("UPDATE system_prompt_versions SET is_active = 0 WHERE is_active = 1")
            cursor = conn.execute("""
                INSERT INTO system_prompt_versions (version, prompt_text, created_at, created_by, rationale, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (version, prompt_text, datetime.now(UTC).isoformat(), created_by, rationale))
            conn.commit()
            logger.info(f"Saved prompt version {version}")
            return cursor.lastrowid

    def get_active_version(self) -> Optional[Dict]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM system_prompt_versions WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                return {
                    "id": row[0], "version": row[1], "prompt_text": row[2],
                    "created_at": row[3], "created_by": row[4], "rationale": row[5],
                    "is_active": bool(row[6]),
                }
        return None

    def list_versions(self) -> List[Dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, version, created_at, created_by, rationale, is_active FROM system_prompt_versions ORDER BY id DESC"
            ).fetchall()
            return [
                {"id": r[0], "version": r[1], "created_at": r[2], "created_by": r[3], "rationale": r[4], "is_active": bool(r[5])}
                for r in rows
            ]
