"""PostgreSQL audit logging for compliance rulings."""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from src.models.ruling import AnswerContract


class PostgresAuditStore:
    def __init__(self, database_url: Optional[str] = None):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required when AUDIT_DATABASE_URL is configured") from exc
        self.psycopg = psycopg
        self.database_url = database_url or os.getenv("AUDIT_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("AUDIT_DATABASE_URL or DATABASE_URL must be configured")
        self._init_schema()

    def log_answer(
        self,
        query: str,
        answer: AnswerContract,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        audit_id = str(uuid.uuid4())
        with self.psycopg.connect(self.database_url) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                (audit_id, request_id, session_id, query, status, answer, citations, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    audit_id,
                    request_id,
                    session_id,
                    query,
                    answer.status.value,
                    answer.answer,
                    json.dumps([citation.to_dict() for citation in answer.citations]),
                    json.dumps(answer.metadata),
                    datetime.now(UTC),
                ),
            )
        return audit_id

    def _init_schema(self) -> None:
        with self.psycopg.connect(self.database_url) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    tier TEXT NOT NULL DEFAULT 'free',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS aaoifi_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    standard_number TEXT,
                    standard_type TEXT,
                    source_url TEXT,
                    version TEXT NOT NULL DEFAULT '1.0',
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT REFERENCES aaoifi_documents(document_id),
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    token_count INTEGER,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS compliance_rulings (
                    ruling_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    status TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    request_id TEXT,
                    session_id TEXT,
                    query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_chunks_document_id ON semantic_chunks(document_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compliance_rulings_session_id ON compliance_rulings(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_session_id ON audit_logs(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")


class NullAuditStore:
    def log_answer(
        self,
        query: str,
        answer: AnswerContract,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[str]:
        return None
