import os
import uuid
import hashlib
import requests
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.acquisition.egypt_financial.models import Base, InstitutionRegistry, DocumentArtifact, DiscoveryStatus, DocumentType

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///l6_evidence.db")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = "l6_evidence_artifacts"

ARTIFACTS_DIR = "artifacts/l6_scrape/raw"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

class CrawlerEngine:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def crawl_institution(self, institution: InstitutionRegistry):
        if institution.discovery_status != DiscoveryStatus.verified or not institution.official_website:
            print(f"Skipping {institution.institution_id} - no verified website.")
            return

        print(f"Crawling {institution.official_website}...")
        
        # Simulate crawling main page
        content = self._fetch_url(institution.official_website)
        if not content:
            return
            
        content_hash = hashlib.sha256(content).hexdigest()
        file_path = os.path.join(ARTIFACTS_DIR, f"{institution.institution_id}_main.html")
        
        with open(file_path, "wb") as f:
            f.write(content)

        # Upload to Supabase if configured
        storage_path = None
        if SUPABASE_URL and SUPABASE_KEY:
            storage_path = self._upload_to_supabase(file_path, f"{institution.institution_id}/{content_hash}.html", "text/html")
        
        session = self.Session()
        # Track the artifact
        artifact = DocumentArtifact(
            artifact_id=str(uuid.uuid4()),
            institution_id=institution.institution_id,
            source_url=institution.official_website,
            document_type=DocumentType.product_page, # Mock classification
            content_type="text/html",
            content_hash=content_hash,
            raw_path=storage_path or file_path,
            http_status=200,
            access_status="public",
            retrieved_at=datetime.utcnow()
        )
        
        session.add(artifact)
        session.commit()
        print(f"Captured artifact {artifact.artifact_id} for {institution.institution_id}")
        session.close()

    def _fetch_url(self, url: str) -> bytes:
        # In a real scenario, this would use Playwright to render JS
        try:
            headers = {'User-Agent': 'Mushir-Evidence-Bot/1.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return b""

    def _upload_to_supabase(self, local_path: str, remote_path: str, content_type: str) -> str:
        """Uploads file using Supabase Storage REST API."""
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{remote_path}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": content_type
        }
        try:
            with open(local_path, 'rb') as f:
                resp = requests.post(upload_url, headers=headers, data=f)
                if resp.status_code in (200, 201):
                    print(f"Uploaded {remote_path} to Supabase successfully.")
                    return upload_url
                else:
                    print(f"Failed to upload to Supabase: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Upload exception: {e}")
        return local_path

    def run_crawl_jobs(self):
        session = self.Session()
        # Find all verified institutions
        institutions = session.query(InstitutionRegistry).filter(
            InstitutionRegistry.discovery_status == DiscoveryStatus.verified
        ).all()
        
        for inst in institutions:
            self.crawl_institution(inst)
            
        session.close()

if __name__ == "__main__":
    crawler = CrawlerEngine()
    crawler.run_crawl_jobs()
