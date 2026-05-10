import asyncio
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from src.config.logging_config import setup_logging
from src.models.document import AAOIFIDocument

logger = setup_logging()

class AAOIFIScraper:
    """Web scraper for AAOIFI standards."""

    def __init__(self, base_url: str = "https://aaoifi.com"):
        self.base_url = base_url.rstrip("/")
        self.standards_url = f"{self.base_url}/accounting-standards-2/?lang=en"

    async def scrape_standards_list(self) -> List[Dict[str, str]]:
        """Scrape list of AAOIFI standards."""
        standards = []
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            page: Page = await browser.new_page()
            try:
                logger.info(f"Navigating to {self.standards_url}")
                await page.goto(self.standards_url, wait_until="networkidle")
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link["href"]
                    text = link.get_text(strip=True)
                    if "standard" in href.lower() or "fas" in text.lower():
                        full_url = href if href.startswith("http") else self.base_url + href
                        standards.append({
                            "title": text,
                            "url": full_url,
                        })
                logger.info(f"Found {len(standards)} standards")
            finally:
                await browser.close()
        return standards

    async def scrape_standard(self, standard_url: str) -> Optional[AAOIFIDocument]:
        """Download and parse individual standard."""
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=True)
            page: Page = await browser.new_page()
            try:
                logger.info(f"Scraping standard: {standard_url}")
                await page.goto(standard_url, wait_until="networkidle")
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                title = soup.find("h1") or soup.find("title")
                title_text = title.get_text(strip=True) if title else "Unknown"
                for element in soup.find_all(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                text = soup.get_text(separator="\n", strip=True)
                doc = AAOIFIDocument(
                    document_id=standard_url.split("/")[-1],
                    title=title_text,
                    content=text,
                    source_url=standard_url,
                )
                return doc
            except Exception as e:
                logger.error(f"Failed to scrape {standard_url}: {e}")
                return None
            finally:
                await browser.close()

    async def scrape_all_with_retry(self, max_retries: int = 3) -> List[AAOIFIDocument]:
        """Scrape all standards with retry logic."""
        standards_list = await self.scrape_standards_list()
        documents = []
        for std in standards_list:
            for attempt in range(max_retries):
                doc = await self.scrape_standard(std["url"])
                if doc:
                    documents.append(doc)
                    break
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {std['url']}")
                await asyncio.sleep(2 ** attempt)
        return documents
