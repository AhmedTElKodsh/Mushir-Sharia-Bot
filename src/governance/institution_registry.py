"""Canonical institution registry records for the Egypt evidence corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional


class InstitutionRegulator(str, Enum):
    CBE = "cbe"
    FRA = "fra"
    EGX = "egx"
    MCSD = "mcsd"
    UNKNOWN = "unknown"


class InstitutionSector(str, Enum):
    BANK = "bank"
    PAYMENT_SERVICE = "payment_service"
    CAPITAL_MARKET = "capital_market"
    INSURANCE = "insurance"
    TAKAFUL = "takaful"
    MORTGAGE_FINANCE = "mortgage_finance"
    LEASING = "leasing"
    CONSUMER_FINANCE = "consumer_finance"
    MICROFINANCE = "microfinance"
    SME_FINANCE = "sme_finance"
    FINTECH = "fintech"
    FUND = "fund"
    SUKUK = "sukuk"
    NON_BANK_FINANCE = "non_bank_finance"
    UNKNOWN = "unknown"


class InstitutionRefreshStatus(str, Enum):
    BASELINE_UNVERIFIED = "baseline_unverified"
    REGULATOR_REVALIDATED = "regulator_revalidated"
    STALE = "stale"
    REJECTED = "rejected"


class InstitutionDiscoveryStatus(str, Enum):
    NOT_STARTED = "not_started"
    OFFICIAL_SITE_CONFIRMED = "official_site_confirmed"
    OFFICIAL_SITE_NOT_FOUND = "official_site_not_found"
    SITE_UNREACHABLE = "site_unreachable"
    BLOCKED_BY_SECURITY = "blocked_by_security"
    REQUIRES_LOGIN = "requires_login"
    DOCUMENT_NOT_PUBLIC = "document_not_public"
    INSUFFICIENT_PUBLIC_DATA = "insufficient_public_data"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


def stable_institution_id(name: str, regulator: InstitutionRegulator, sector: InstitutionSector) -> str:
    """Return a stable, human-readable ID for baseline registry seeds."""
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    if not normalized:
        raise ValueError("institution name must produce a stable id")
    return f"{regulator.value}-{sector.value}-{normalized}"


@dataclass(frozen=True)
class InstitutionRegistryRecord:
    """Baseline institution row with explicit provenance and refresh state."""

    institution_id: str
    name_en: str
    regulator: InstitutionRegulator
    sector: InstitutionSector
    registry_source: str
    registry_source_url: str
    refresh_status: InstitutionRefreshStatus = InstitutionRefreshStatus.BASELINE_UNVERIFIED
    discovery_status: InstitutionDiscoveryStatus = InstitutionDiscoveryStatus.NOT_STARTED
    name_ar: Optional[str] = None
    country: str = "EG"
    official_website: Optional[str] = None
    official_website_confidence: float = 0.0
    attempt_count: int = 0
    last_checked_at: Optional[date] = None
    gap_reason: str = ""
    notes: str = ""
    baseline_inputs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.institution_id.strip():
            raise ValueError("institution_id is required")
        if not self.name_en.strip():
            raise ValueError("name_en is required")
        if self.regulator == InstitutionRegulator.UNKNOWN:
            raise ValueError("regulator provenance is required")
        if self.sector == InstitutionSector.UNKNOWN:
            raise ValueError("regulator category/sector is required")
        if not self.registry_source.strip():
            raise ValueError("registry_source is required")
        if not self.registry_source_url.startswith(("https://", "http://")):
            raise ValueError("registry_source_url must be an HTTP(S) URL")
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        if not 0.0 <= self.official_website_confidence <= 1.0:
            raise ValueError("official_website_confidence must be between 0 and 1")
        if self.discovery_status != InstitutionDiscoveryStatus.NOT_STARTED and self.attempt_count == 0:
            raise ValueError("discovery_status requires attempt_count")
        if self.discovery_status in {
            InstitutionDiscoveryStatus.OFFICIAL_SITE_NOT_FOUND,
            InstitutionDiscoveryStatus.SITE_UNREACHABLE,
            InstitutionDiscoveryStatus.BLOCKED_BY_SECURITY,
            InstitutionDiscoveryStatus.REQUIRES_LOGIN,
            InstitutionDiscoveryStatus.DOCUMENT_NOT_PUBLIC,
            InstitutionDiscoveryStatus.INSUFFICIENT_PUBLIC_DATA,
            InstitutionDiscoveryStatus.MANUAL_REVIEW_REQUIRED,
        } and not self.gap_reason.strip():
            raise ValueError("gap_reason is required for non-success discovery gaps")

    @classmethod
    def baseline(
        cls,
        *,
        name_en: str,
        regulator: InstitutionRegulator,
        sector: InstitutionSector,
        registry_source: str,
        registry_source_url: str,
        **kwargs: object,
    ) -> "InstitutionRegistryRecord":
        return cls(
            institution_id=stable_institution_id(name_en, regulator, sector),
            name_en=name_en,
            regulator=regulator,
            sector=sector,
            registry_source=registry_source,
            registry_source_url=registry_source_url,
            **kwargs,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "InstitutionRegistryRecord":
        data = dict(payload)
        data["regulator"] = InstitutionRegulator(data["regulator"])
        data["sector"] = InstitutionSector(data["sector"])
        data["refresh_status"] = InstitutionRefreshStatus(
            data.get("refresh_status", InstitutionRefreshStatus.BASELINE_UNVERIFIED)
        )
        data["discovery_status"] = InstitutionDiscoveryStatus(
            data.get("discovery_status", InstitutionDiscoveryStatus.NOT_STARTED)
        )
        if isinstance(data.get("last_checked_at"), str):
            data["last_checked_at"] = date.fromisoformat(str(data["last_checked_at"]))
        return cls(**data)

    def to_dict(self) -> Dict[str, object]:
        return {
            "institution_id": self.institution_id,
            "name_en": self.name_en,
            "name_ar": self.name_ar,
            "country": self.country,
            "regulator": self.regulator.value,
            "sector": self.sector.value,
            "registry_source": self.registry_source,
            "registry_source_url": self.registry_source_url,
            "refresh_status": self.refresh_status.value,
            "discovery_status": self.discovery_status.value,
            "official_website": self.official_website,
            "official_website_confidence": self.official_website_confidence,
            "attempt_count": self.attempt_count,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "gap_reason": self.gap_reason,
            "notes": self.notes,
            "baseline_inputs": self.baseline_inputs,
        }


class InstitutionRegistry:
    """Strict in-memory registry for baseline and revalidated institutions."""

    def __init__(self, records: Iterable[InstitutionRegistryRecord] = ()) -> None:
        self._records: Dict[str, InstitutionRegistryRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: InstitutionRegistryRecord) -> None:
        if record.institution_id in self._records:
            raise ValueError(f"duplicate institution_id: {record.institution_id}")
        self._records[record.institution_id] = record

    def get(self, institution_id: str) -> InstitutionRegistryRecord:
        try:
            return self._records[institution_id]
        except KeyError as exc:
            raise KeyError(f"unknown institution_id: {institution_id}") from exc

    def records(self) -> List[InstitutionRegistryRecord]:
        return list(self._records.values())

    def by_sector(self, sector: InstitutionSector) -> List[InstitutionRegistryRecord]:
        return [record for record in self._records.values() if record.sector == sector]

    def by_regulator(self, regulator: InstitutionRegulator) -> List[InstitutionRegistryRecord]:
        return [record for record in self._records.values() if record.regulator == regulator]

    @classmethod
    def from_payload(cls, records: Iterable[Mapping[str, object]]) -> "InstitutionRegistry":
        return cls(InstitutionRegistryRecord.from_mapping(record) for record in records)
