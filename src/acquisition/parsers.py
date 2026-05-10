import pdfplumber
from bs4 import BeautifulSoup
from typing import Optional
from src.config.logging_config import setup_logging

logger = setup_logging()

def parse_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF file."""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        content = "\n".join(text_parts).strip()
        if not content:
            logger.warning(f"No text extracted from PDF: {file_path}")
            return None
        return content
    except Exception as e:
        logger.error(f"Failed to parse PDF {file_path}: {e}")
        raise

def parse_html(html_content: str) -> str:
    """Extract clean text from HTML content."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for element in soup.find_all(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        content = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to parse HTML: {e}")
        raise
