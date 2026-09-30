"""Local review-card loading; eligibility metadata is not a ruling or authentication.

No source acquisition, precedence selection, outcome evaluation, queue promotion,
or runtime integration is performed here. Historical versions remain available.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date as CalendarDate
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, field_validator, model_validator

from src.models.evidence import EvidenceModel, Scalar, Text, Version, require_human_reviewer

MAX_RULE_FILE_BYTES = 1_000_000


def _single_question(question: str) -> str:
    if question.count("?") + question.count("\u061f") != 1 or "\n" in question or "\r" in question:
        raise ValueError("each fact question must contain one question")
    return question


class _FrozenDict(dict):
    def _immutable(self, *args, **kwargs):
        raise TypeError("rule conditions are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


class ScholarSignoff(EvidenceModel):
    reviewer_id: Text | None = None
    date: CalendarDate | None = None
    decision: Literal["pending", "approved", "rejected"] = "pending"

    @field_validator("date", mode="before")
    @classmethod
    def calendar_date_only(cls, value):
        if value is not None and type(value) not in (CalendarDate, str):
            raise ValueError("signoff date must be a calendar date")
        return value

    @model_validator(mode="after")
    def approved_identity(self):
        if self.decision == "approved":
            if self.reviewer_id is None or self.date is None:
                raise ValueError("approved signoff requires reviewer identity and date")
            require_human_reviewer(self.reviewer_id)
        return self


class RuleOutcome(EvidenceModel):
    when: dict[Text, Scalar] = Field(min_length=1)
    outcome: Text

    @field_validator("when")
    @classmethod
    def freeze_conditions(cls, value):
        return _FrozenDict(value)


class RuleCard(EvidenceModel):
    rule_id: Text
    version: Version
    source_authority: Literal["client_rulebook", "aaoifi_ss", "iifa"]
    source_anchor: Text
    applies_to_archetypes: tuple[Text, ...] = Field(min_length=1)
    material_facts: tuple[Text, ...] = Field(min_length=1)
    outcomes: tuple[RuleOutcome, ...] = Field(min_length=1)
    unknown_fact_question: Text
    unknown_fact_questions: dict[Text, Text] = Field(default_factory=dict)
    precedence_note: Text | None = None
    scholar_signoff: ScholarSignoff
    status: Literal["draft", "approved", "superseded"]

    @field_validator("unknown_fact_questions")
    @classmethod
    def freeze_questions(cls, value):
        for question in value.values():
            _single_question(question)
        return _FrozenDict(value)

    @field_validator("unknown_fact_question")
    @classmethod
    def single_default_question(cls, value):
        return _single_question(value)

    @model_validator(mode="after")
    def coherent_card(self):
        if len(set(self.material_facts)) != len(self.material_facts):
            raise ValueError("duplicate material facts")
        if not set(self.unknown_fact_questions).issubset(self.material_facts):
            raise ValueError("fact question must target a declared material fact")
        if len(set(self.applies_to_archetypes)) != len(self.applies_to_archetypes):
            raise ValueError("duplicate archetypes")
        for outcome in self.outcomes:
            if not set(outcome.when).issubset(self.material_facts):
                raise ValueError("outcome condition must name declared material facts")
        for index, left in enumerate(self.outcomes):
            for right in self.outcomes[index + 1:]:
                common = set(left.when) & set(right.when)
                if all(type(left.when[key]) is type(right.when[key]) and left.when[key] == right.when[key]
                       for key in common):
                    raise ValueError("overlapping outcome conditions require explicit adjudication")
        if self.status == "approved":
            if self.scholar_signoff.decision != "approved" or self.precedence_note is None:
                raise ValueError("approved card requires approved signoff and explicit precedence note")
        return self

    @property
    def runtime_eligible(self) -> bool:
        """Metadata eligibility only, never a computed verdict."""
        return self.status == "approved" and self.scholar_signoff.decision == "approved"


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys, merge keys and aliases rather than silently overwriting."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.events.AliasEvent):
            raise ValueError("YAML aliases are not supported")
        return super().compose_node(parent, index)


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ValueError("YAML merge keys are not supported")
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("YAML mapping keys must be strings")
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_rule_cards(source: str | Path | Mapping | Iterable[Mapping]) -> tuple[RuleCard, ...]:
    """Load a local YAML path, one mapping, or a sequence of mappings.

    YAML documents contain one card or a list of cards. Duplicate (id, version)
    pairs and multiple approved versions of an ID fail; no latest-version policy
    or automatic supersession is invented by the loader.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.stat().st_size > MAX_RULE_FILE_BYTES:
            raise ValueError("rule file exceeds the size limit")
        payload = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    else:
        payload = source
    if isinstance(payload, Mapping):
        payload = [payload]
    if not isinstance(payload, Iterable) or isinstance(payload, (str, bytes)):
        raise ValueError("rule source must contain a card mapping or sequence")
    cards = []
    seen = set()
    approved_ids = set()
    for item in payload:
        if not isinstance(item, Mapping):
            raise ValueError("each rule card must be a mapping")
        card = RuleCard.model_validate(item)
        key = (card.rule_id, card.version)
        if key in seen:
            raise ValueError(f"duplicate rule ID/version: {key}")
        if card.runtime_eligible and card.rule_id in approved_ids:
            raise ValueError(f"multiple approved versions of rule: {card.rule_id}")
        seen.add(key)
        if card.runtime_eligible:
            approved_ids.add(card.rule_id)
        cards.append(card)
    return tuple(cards)


def approved_rule_cards(source: str | Path | Mapping | Iterable[Mapping]) -> tuple[RuleCard, ...]:
    """Return only structurally eligible cards, preserving their ID and version."""
    return tuple(card for card in load_rule_cards(source) if card.runtime_eligible)
