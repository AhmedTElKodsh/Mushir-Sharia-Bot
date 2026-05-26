"""Durable, human-only scholar review records for governance gates."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.models.ruling import AnswerContract


class ScholarReviewTargetType(str, Enum):
    ANSWER = "answer"
    RULE_EVALUATION = "rule_evaluation"
    RETRIEVAL_CASE = "retrieval_case"
    SOURCE_CATALOG = "source_catalog"


class ScholarReviewDecision(str, Enum):
    ACCEPTED_FOR_GOLD_SET = "accepted_for_gold_set"
    ACCEPTED_WITH_CORRECTION = "accepted_with_correction"
    REJECTED_UNSUPPORTED = "rejected_unsupported"
    WRONG_STANDARD = "wrong_standard"
    STALE_SOURCE = "stale_source"
    TRANSLATION_ISSUE = "translation_issue"
    UNSAFE_ANSWER = "unsafe_answer"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


@dataclass(frozen=True)
class ScholarReviewEvidenceGate:
    """Manual review decision tied to source, citation, and optional rule evidence."""

    review_id: str
    target_type: ScholarReviewTargetType
    target_id: str
    reviewer_id: str
    decision: ScholarReviewDecision
    source_ids: List[str]
    citation_ids: List[str]
    rationale: str
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rule_id: Optional[str] = None
    rule_version: Optional[str] = None
    correction_type: str = ""
    uncertainty_flags: List[str] = field(default_factory=list)
    model_confidence: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id is required")
        if not self.target_id.strip():
            raise ValueError("target_id is required")
        if not self.reviewer_id.strip():
            raise ValueError("reviewer_id is required")
        if self.reviewer_id.lower() in {"model", "llm", "model-confidence", "auto"}:
            raise ValueError("scholar review cannot be promoted by model confidence")
        if not self.source_ids or not self.citation_ids:
            raise ValueError("source_ids and citation_ids are required")
        if not self.rationale.strip():
            raise ValueError("rationale is required")
        if self.model_confidence is not None:
            raise ValueError("scholar review cannot be promoted by model confidence")
        if self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must include timezone")
        if bool(self.rule_id) != bool(self.rule_version):
            raise ValueError("rule_id and rule_version must be supplied together")

    @property
    def is_gold_candidate(self) -> bool:
        return self.decision in {
            ScholarReviewDecision.ACCEPTED_FOR_GOLD_SET,
            ScholarReviewDecision.ACCEPTED_WITH_CORRECTION,
        }

    @property
    def can_update_runtime_governance(self) -> bool:
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "target_type": self.target_type.value,
            "target_id": self.target_id,
            "reviewer_id": self.reviewer_id,
            "decision": self.decision.value,
            "source_ids": self.source_ids,
            "citation_ids": self.citation_ids,
            "rationale": self.rationale,
            "reviewed_at": self.reviewed_at.isoformat(),
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "correction_type": self.correction_type,
            "uncertainty_flags": self.uncertainty_flags,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ScholarReviewEvidenceGate":
        data = dict(payload)
        data["target_type"] = ScholarReviewTargetType(data["target_type"])
        data["decision"] = ScholarReviewDecision(data["decision"])
        if isinstance(data.get("reviewed_at"), str):
            data["reviewed_at"] = datetime.fromisoformat(data["reviewed_at"])
        return cls(**data)


class ScholarReviewStore:
    """Append-only JSONL store for auditable scholar review records."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: ScholarReviewEvidenceGate) -> None:
        existing_ids = {item.review_id for item in self.load()}
        if record.review_id in existing_ids:
            raise ValueError(f"duplicate review_id: {record.review_id}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def extend(self, records: Iterable[ScholarReviewEvidenceGate]) -> None:
        for record in records:
            self.append(record)

    def load(self) -> List[ScholarReviewEvidenceGate]:
        if not self.path.exists():
            return []
        records: List[ScholarReviewEvidenceGate] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(ScholarReviewEvidenceGate.from_mapping(json.loads(line)))
        return records


class ScholarReviewWorkflowStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"


@dataclass(frozen=True)
class ScholarReviewPacket:
    """Review-only packet generated by the running app for human scholars.

    This packet is intentionally separate from runtime governance. It can help a
    scholar review model/rule traces and AAOIFI references, but it cannot promote
    an answer or mapping into production authority.
    """

    review_id: str
    query: str
    answer: AnswerContract
    workflow_status: ScholarReviewWorkflowStatus

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id is required")
        if not self.query.strip():
            raise ValueError("query is required")

    @property
    def can_update_runtime_governance(self) -> bool:
        return False

    def metadata(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "workflow_status": self.workflow_status.value,
            "path": "scholar_review_enhancement",
            "blocks_main_app": False,
            "can_update_runtime_governance": self.can_update_runtime_governance,
            "human_review_status": self.workflow_status.value,
            "export_ready": self.workflow_status == ScholarReviewWorkflowStatus.PENDING,
        }

    def rows(self) -> List[Dict[str, object]]:
        metadata = self.answer.metadata or {}
        scenario = metadata.get("transaction_scenario", {}) or {}
        route = metadata.get("standards_route", {}) or {}
        rule = metadata.get("rule_evaluation", {}) or {}
        verdict = metadata.get("verdict_contract", {}) or {}
        citations = self.answer.citations or []
        if not citations:
            citations = [None]
        rows: List[Dict[str, object]] = []
        for index, citation in enumerate(citations, start=1):
            rows.append(
                {
                    "review_id": self.review_id,
                    "review_item_number": index,
                    "query": self.query,
                    "app_status": self.answer.status.value,
                    "app_answer": self.answer.answer,
                    "response_language": metadata.get("response_language", ""),
                    "workflow_status": self.workflow_status.value,
                    "review_path": "scholar_review_enhancement",
                    "blocks_main_app": "false",
                    "runtime_governance_update_allowed": "false",
                    "question_type": scenario.get("question_type", ""),
                    "contract_family": scenario.get("contract_family", ""),
                    "missing_facts": _join(rule.get("missing_facts") or scenario.get("missing_facts")),
                    "uncertainties": _join(scenario.get("uncertainties")),
                    "route_id": route.get("route_id", ""),
                    "candidate_standards": _join(route.get("candidate_standards")),
                    "primary_source_families": _join(route.get("primary")),
                    "requires_rule_evaluation": str(route.get("requires_rule_evaluation", "")).lower(),
                    "rule_id": rule.get("rule_id", ""),
                    "rule_version": rule.get("rule_version", ""),
                    "matched_rules": _join(rule.get("matched_rules")),
                    "evidence_requirements": _join(rule.get("evidence_requirements")),
                    "human_review_flags": _join(rule.get("human_review_flags")),
                    "source_families_retrieved": _join(metadata.get("source_families")),
                    "verdict": verdict.get("verdict", ""),
                    "verdict_requires_scholar_review": str(verdict.get("requires_scholar_review", "")).lower(),
                    "standard_number": citation.standard_number if citation else "",
                    "section_number": citation.section_number if citation else "",
                    "section_title": citation.section_title if citation else "",
                    "document_id": citation.document_id if citation else "",
                    "evidence_excerpt": citation.excerpt if citation else "",
                    "citation_confidence": (
                        f"{citation.confidence_score:.2f}"
                        if citation and citation.confidence_score is not None
                        else ""
                    ),
                    "human_scholar_review": "",
                    "human_scholar_review_references": "",
                    "human_scholar_review_notes": "",
                }
            )
        return rows

    def markdown(self) -> str:
        rows = self.rows()
        header = [
            "# Scholar Review Packet",
            "",
            f"- Review ID: {self.review_id}",
            f"- Workflow status: {self.workflow_status.value}",
            "- Runtime governance update: not allowed from this packet",
            "",
            "## App Output",
            "",
            f"Status: {self.answer.status.value}",
            "",
            self.answer.answer,
            "",
            "## Review Rows",
            "",
            "| Item | Standard | Section | Route | Rule | Human review |",
            "|---|---|---|---|---|---|",
        ]
        for row in rows:
            header.append(
                "| {item} | {standard} | {section} | {route} | {rule} |  |".format(
                    item=row["review_item_number"],
                    standard=row["standard_number"],
                    section=row["section_number"],
                    route=row["route_id"],
                    rule=row["rule_id"],
                )
            )
        header.extend(["", "## Evidence Excerpts", ""])
        for row in rows:
            excerpt = str(row["evidence_excerpt"]).replace("\n", " ").strip()
            header.append(
                f"{row['review_item_number']}. {row['standard_number']} {row['section_number']}: {excerpt}"
            )
        return "\n".join(header).rstrip() + "\n"

    @classmethod
    def from_answer(
        cls,
        *,
        review_id: str,
        query: str,
        answer: AnswerContract,
    ) -> "ScholarReviewPacket":
        metadata = answer.metadata or {}
        review_meta = metadata.get("scholar_review_workflow", {}) or {}
        required = bool(review_meta.get("required")) or bool(
            (metadata.get("rule_evaluation", {}) or {}).get("human_review_flags")
        )
        return cls(
            review_id=review_id,
            query=query,
            answer=answer,
            workflow_status=(
                ScholarReviewWorkflowStatus.PENDING
                if required
                else ScholarReviewWorkflowStatus.NOT_REQUIRED
            ),
        )


class ScholarReviewPacketCsvStore:
    """Export app-generated review packets in a scholar-readable CSV shape."""

    FIELDS: Sequence[str] = (
        "review_id",
        "review_item_number",
        "query",
        "app_status",
        "app_answer",
        "response_language",
        "workflow_status",
        "review_path",
        "blocks_main_app",
        "runtime_governance_update_allowed",
        "question_type",
        "contract_family",
        "missing_facts",
        "uncertainties",
        "route_id",
        "candidate_standards",
        "primary_source_families",
        "requires_rule_evaluation",
        "rule_id",
        "rule_version",
        "matched_rules",
        "evidence_requirements",
        "human_review_flags",
        "source_families_retrieved",
        "verdict",
        "verdict_requires_scholar_review",
        "standard_number",
        "section_number",
        "section_title",
        "document_id",
        "evidence_excerpt",
        "citation_confidence",
        "human_scholar_review",
        "human_scholar_review_references",
        "human_scholar_review_notes",
    )

    @classmethod
    def export_packet(cls, path: str | Path, packet: ScholarReviewPacket) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=cls.FIELDS)
            writer.writeheader()
            writer.writerows(packet.rows())


class ScholarReviewPacketMarkdownStore:
    """Export app-generated review packets as a compact human-readable brief."""

    @staticmethod
    def export_packet(path: str | Path, packet: ScholarReviewPacket) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(packet.markdown(), encoding="utf-8")


def _join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable):
        return "|".join(str(item) for item in value)
    return str(value)
