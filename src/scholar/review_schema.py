"""Structured scholar review form for Q1/Q2/Q3 queue items."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ScholarReview(BaseModel):
    query_id: str = Field(min_length=1)
    scholar_name: str = Field(min_length=1)
    scholar_institution: str = Field(min_length=1)
    ruling_accuracy: Literal["CORRECT", "WRONG", "PARTIALLY_CORRECT"]
    standard_citation: Literal["CORRECT", "WRONG", "MISSING"]
    disagreement_disclosed: Literal["YES", "NO", "NA"]
    severity_if_wrong: Literal["CRITICAL", "HIGH", "MEDIUM", "NA"]
    corrected_answer_ar: Optional[str] = None
    corrected_ruling: Optional[str] = None
    corrected_standards: Optional[list[str]] = None
    review_timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    new_edge_case: bool = False
    scholar_notes: str = ""
    dalil: str = ""
    conditions: list[str] = Field(default_factory=list)

    @field_validator("query_id", "scholar_name", "scholar_institution", "review_timestamp")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field cannot be blank")
        return stripped

    @field_validator("corrected_standards", mode="before")
    @classmethod
    def split_corrected_standards(cls, value):
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.replace("،", ",").split(",") if item.strip()]
        return value

    @field_validator("conditions", mode="before")
    @classmethod
    def split_conditions(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.replace("،", ",").split(",") if item.strip()]
        return value

    @property
    def scholar_sign_off(self) -> str:
        return "DONE"

    @property
    def requires_ontology_patch(self) -> bool:
        return self.ruling_accuracy in {"WRONG", "PARTIALLY_CORRECT"} or self.standard_citation in {
            "WRONG",
            "MISSING",
        }
