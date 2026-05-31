import os
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.acquisition.egypt_financial.models import Base, DocumentArtifact

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///l6_evidence.db")

class ExtractorEngine:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def extract_artifacts(self):
        session = self.Session()
        
        # Find raw captured artifacts that need text extraction
        artifacts = session.query(DocumentArtifact).filter(
            DocumentArtifact.raw_path.isnot(None),
            DocumentArtifact.text_path.is_(None)
        ).all()
        
        for doc in artifacts:
            print(f"Extracting text for {doc.artifact_id}...")
            
            # Since Supabase URLs or local files could be used
            # We'll handle local file extraction for HTML
            if os.path.exists(doc.raw_path) and doc.content_type == "text/html":
                with open(doc.raw_path, "r", encoding="utf-8", errors="ignore") as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, "html.parser")
                text_content = soup.get_text(separator="\n", strip=True)
                
                text_file_path = doc.raw_path.replace(".html", ".txt")
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                
                doc.text_path = text_file_path
                doc.extraction_status = "success"
                
        session.commit()
        session.close()
        print("Extraction complete.")

if __name__ == "__main__":
    extractor = ExtractorEngine()
    extractor.extract_artifacts()
