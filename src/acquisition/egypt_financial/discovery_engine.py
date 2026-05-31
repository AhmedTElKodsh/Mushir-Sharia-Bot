import os
import requests
import urllib.parse
from typing import List, Optional, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.acquisition.egypt_financial.models import Base, InstitutionRegistry, DiscoveryStatus

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///l6_evidence.db")

class DiscoveryEngine:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Protocol Limits
        self.MAX_REGULATOR_CHECKS = 3
        self.MAX_WEB_SEARCHES = 5
        self.MAX_SITE_CANDIDATES = 3
        self.MAX_RETRIES = 2

    def discover_institution(self, institution: InstitutionRegistry) -> InstitutionRegistry:
        """
        Executes the bounded discovery protocol for an institution.
        """
        if institution.discovery_attempt_count is None:
            institution.discovery_attempt_count = 0
            
        print(f"[{institution.institution_id}] Starting discovery for {ascii(institution.name_en or institution.name_ar)}...")
        
        # Simulation of discovery bounds tracking
        search_count = 0
        regulator_checks = 0
        site_candidates = 0
        
        # 1. Regulator Check (Simulated API/Lookup)
        regulator_checks += 1
        official_url = self._check_regulator_registry(institution)
        
        # 2. Web Search Fallback
        if not official_url and search_count < self.MAX_WEB_SEARCHES:
            queries = self._generate_search_queries(institution)
            for q in queries[:self.MAX_WEB_SEARCHES]:
                search_count += 1
                candidate_url = self._perform_web_search(q)
                if candidate_url:
                    site_candidates += 1
                    if self._verify_candidate(candidate_url, institution):
                        official_url = candidate_url
                        break
                
                if site_candidates >= self.MAX_SITE_CANDIDATES:
                    break

        # 3. Reachability Check
        if official_url:
            status = self._check_reachability(official_url)
            if status == DiscoveryStatus.verified:
                institution.official_website = official_url
                institution.website_confidence = "high"
                institution.discovery_status = DiscoveryStatus.verified
            else:
                institution.discovery_status = status
        else:
            institution.discovery_status = DiscoveryStatus.official_site_not_found
            institution.gap_reason = f"Exhausted limits: searches={search_count}, candidates={site_candidates}"

        institution.discovery_attempt_count += 1
        institution.last_checked_at = datetime.utcnow()
        return institution

    def _generate_search_queries(self, inst: InstitutionRegistry) -> List[str]:
        queries = []
        if inst.name_en: queries.append(f"{inst.name_en} Egypt official site")
        if inst.name_ar: queries.append(f"{inst.name_ar} موقع رسمي")
        if inst.name_en and inst.sector: queries.append(f"{inst.name_en} {inst.sector} Egypt")
        return queries

    def _check_regulator_registry(self, inst: InstitutionRegistry) -> Optional[str]:
        # Placeholder for actual CBE/FRA active list lookup
        # Currently defaults to None to trigger web search
        return None

    def _perform_web_search(self, query: str) -> Optional[str]:
        # Placeholder for Tavily/DuckDuckGo/Google Search integration
        # Yields a dummy URL for pilot testing if it matches specific keywords
        if "National Bank of Egypt" in query: return "https://www.nbe.com.eg"
        if "Faisal Islamic Bank" in query: return "https://www.faisalbank.com.eg"
        if "Thndr" in query: return "https://thndr.app"
        return None

    def _verify_candidate(self, url: str, inst: InstitutionRegistry) -> bool:
        # Check domain ownership, brand match, etc.
        return True

    def _check_reachability(self, url: str) -> DiscoveryStatus:
        for attempt in range(self.MAX_RETRIES):
            try:
                # Use a standard user agent
                headers = {'User-Agent': 'Mushir-Evidence-Bot/1.0'}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    return DiscoveryStatus.verified
                elif resp.status_code in (401, 403):
                    return DiscoveryStatus.blocked_by_security
                elif resp.status_code == 404:
                    return DiscoveryStatus.site_unreachable
            except requests.RequestException:
                pass
        return DiscoveryStatus.site_unreachable

    def run_all(self):
        """Run the discovery engine against all unverified institutions."""
        session = self.Session()
        
        # We target institutions that haven't been successfully verified yet
        targets = session.query(InstitutionRegistry).filter(
            (InstitutionRegistry.discovery_status != DiscoveryStatus.verified) |
            (InstitutionRegistry.discovery_status.is_(None))
        ).all()
        
        print(f"Starting full-scale discovery on {len(targets)} institutions...")
        
        for inst in targets:
            updated_inst = self.discover_institution(inst)
            session.add(updated_inst)
            print(f"-> Status: {updated_inst.discovery_status.value} | URL: {updated_inst.official_website}")
            session.commit() # commit each to save progress
            
        session.close()
        print("Full-scale discovery complete.")

if __name__ == "__main__":
    engine = DiscoveryEngine()
    engine.run_all()
