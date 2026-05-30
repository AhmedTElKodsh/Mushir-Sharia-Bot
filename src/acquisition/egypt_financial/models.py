import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DiscoveryStatus(str, enum.Enum):
    verified = "verified"
    official_site_not_found = "official_site_not_found"
    site_unreachable = "site_unreachable"
    blocked_by_security = "blocked_by_security"
    requires_login = "requires_login"
    document_not_public = "document_not_public"
    insufficient_public_data = "insufficient_public_data"
    manual_review_required = "manual_review_required"
    inactive_or_superseded = "inactive_or_superseded"

class DocumentType(str, enum.Enum):
    tariff_sheet = "tariff_sheet"
    terms_and_conditions = "terms_and_conditions"
    contract = "contract"
    model_contract = "model_contract"
    prospectus = "prospectus"
    annual_report = "annual_report"
    fund_document = "fund_document"
    policy_wording = "policy_wording"
    product_page = "product_page"
    rulebook = "rulebook"
    disclosure = "disclosure"
    unknown = "unknown"

class InstitutionRegistry(Base):
    __tablename__ = 'institution_registry'

    institution_id = Column(String, primary_key=True)
    name_en = Column(String, nullable=True)
    name_ar = Column(String, nullable=True)
    sector = Column(String, nullable=False)
    subsector = Column(String, nullable=True)
    regulator = Column(String, nullable=False)
    license_status = Column(String, nullable=True)
    registry_source_url = Column(String, nullable=True)
    registry_source_date = Column(DateTime, nullable=True)
    official_website = Column(String, nullable=True)
    website_confidence = Column(String, nullable=True)
    discovery_status = Column(Enum(DiscoveryStatus), nullable=True)
    discovery_attempt_count = Column(Integer, default=0)
    last_checked_at = Column(DateTime, nullable=True)
    gap_reason = Column(String, nullable=True)
    review_status = Column(String, nullable=True)

class DocumentArtifact(Base):
    __tablename__ = 'document_artifact'

    artifact_id = Column(String, primary_key=True)
    institution_id = Column(String, ForeignKey('institution_registry.institution_id'))
    source_url = Column(String, nullable=False)
    source_rank = Column(Integer, default=0)
    document_type = Column(Enum(DocumentType), default=DocumentType.unknown)
    title = Column(String, nullable=True)
    language = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    http_status = Column(Integer, nullable=True)
    content_type = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    raw_path = Column(String, nullable=True)
    text_path = Column(String, nullable=True)
    extraction_status = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    citation_anchor_strategy = Column(String, nullable=True)
    access_status = Column(String, nullable=True)
