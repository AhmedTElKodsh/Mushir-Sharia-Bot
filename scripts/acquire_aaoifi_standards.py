#!/usr/bin/env python3
"""Script to acquire AAOIFI standards."""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from src.acquisition.scraper import AAOIFIScraper
from src.acquisition.storage import DocumentStore
from src.config.logging_config import setup_logging

logger = setup_logging()

async def acquire_standards(mode: str = "auto"):
    """Acquire AAOIFI standards."""
    logger.info("Starting AAOIFI standards acquisition...")
    scraper = AAOIFIScraper()
    store = DocumentStore()
    start_time = datetime.now()
    try:
        if mode == "manual":
            standards = await scraper.scrape_standards_list()
            print(f"\nFound {len(standards)} standards:")
            for i, std in enumerate(standards, 1):
                print(f"  {i}. {std['title']} - {std['url']}")
            response = input("\nProceed with download? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        documents = await scraper.scrape_all_with_retry()
        for doc in documents:
            store.store_document(doc)
            logger.info(f"Stored: {doc.document_id}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n=== Acquisition Summary ===")
        print(f"Documents acquired: {len(documents)}")
        print(f"Time elapsed: {elapsed:.2f}s")
        print(f"Storage: {store.db_path}")
    except Exception as e:
        logger.error(f"Acquisition failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acquire AAOIFI standards")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto", help="Acquisition mode")
    args = parser.parse_args()
    asyncio.run(acquire_standards(args.mode))
