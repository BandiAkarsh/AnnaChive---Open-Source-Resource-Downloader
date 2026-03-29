"""Semantic Scholar source connector - AI-powered academic search."""
import os
from pathlib import Path
from typing import Optional

import keyring
from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.semantic_scholar")


def _get_api_key(env_var: str, keyring_name: str) -> Optional[str]:
    """Get API key from environment or keyring."""
    # First try environment variable
    key = os.getenv(env_var)
    if key:
        return key
    # Then try keyring
    try:
        key = keyring.get_password("annchive", keyring_name)
        if key:
            return key
    except Exception:
        pass
    return None


class SemanticScholarSource(BaseSource):
    """Semantic Scholar connector - AI-indexed academic papers.
    
    Uses free API with rate limits. Provides metadata and paper links.
    Full text requires subscription, but metadata is free.
    
    Rate limits:
    - Without API key: 100 requests per 5 minutes
    - With API key: Higher limits
    
    Get API key: https://www.semanticscholar.org/product/api#api-key-form
    Set via: annchive config apikey set semantic-scholar YOUR-KEY
    """
    
    name = "semantic-scholar"
    requires_tor = False
    requires_auth = False  # Works without key, but limited
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self):
        super().__init__()
        # Load API key from environment or keyring
        self._api_key = _get_api_key("ANNCHIVE_SEMANTIC_KEY", "annchive_semantic_key")
        self._client = None
    
    def _get_headers(self) -> dict:
        """Get HTTP headers including API key if available."""
        headers = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Semantic Scholar for papers.
        
        Args:
            query: Search query (title, author, topic)
            limit: Maximum results to return
        
        Returns:
            List of SourceResult objects
        """
        url = f"{self.BASE_URL}/paper/search"
        
        params = {
            "query": query,
            "limit": min(limit, 100),  # API max is 100
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,url",
        }
        
        try:
            response = await self.client.get(
                url, 
                params=params,
                headers=self._get_headers()
            )
            
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                if not self._api_key:
                    logger.info("Get a free API key for higher limits: https://www.semanticscholar.org/product/api")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data.get("data", []))
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse Semantic Scholar API response into SourceResult objects."""
        results = []
        
        for item in items:
            # Extract DOI from external IDs
            doi = None
            if external_ids := item.get("externalIds", {}):
                doi = external_ids.get("DOI")
            
            # Format authors
            authors = item.get("authors", [])
            author_str = ", ".join(a.get("name", "") for a in authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            
            result = SourceResult(
                source=self.name,
                id=item.get("paperId", ""),
                title=item.get("title", "Unknown"),
                author=author_str,
                format="paper",
                published=str(item.get("year", "")),
                doi=doi,
                url=item.get("url"),
                description=item.get("abstract"),
                metadata={
                    "venue": item.get("venue"),
                    "citations": item.get("citationCount", 0),
                    "external_ids": item.get("externalIds", {}),
                },
            )
            results.append(result)
        
        return results
    
    async def get_paper(self, paper_id: str) -> Optional[SourceResult]:
        """Get detailed paper info by paper ID."""
        url = f"{self.BASE_URL}/paper/{paper_id}"
        
        params = {
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,url,doi",
        }
        
        try:
            response = await self.client.get(
                url, 
                params=params,
                headers=self._get_headers()
            )
            
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results([data])[0]
        except Exception as e:
            logger.error(f"Failed to get paper: {e}")
            return None
    
    async def get_download_url(self, paper_id: str) -> Optional[str]:
        """Get paper URL.
        
        Semantic Scholar doesn't host PDFs - returns link to publisher.
        For actual PDF, users need to access the publisher directly.
        """
        return f"https://www.semanticscholar.org/paper/{paper_id}"
    
    async def download(
        self, 
        paper_id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download paper metadata as JSON.
        
        Note: Semantic Scholar doesn't host PDFs. This downloads metadata.
        """
        paper = await self.get_paper(paper_id)
        
        if not paper:
            return None
        
        if not filename:
            filename = f"{paper_id}.json"
        
        output_path = output_dir / filename
        
        import json
        with open(output_path, "w") as f:
            json.dump(paper.metadata, f, indent=2)
        
        logger.info(f"Saved paper metadata: {paper_id}")
        return output_path
    
    async def get_citations(self, paper_id: str, limit: int = 10) -> list[SourceResult]:
        """Get papers that cite the given paper."""
        url = f"{self.BASE_URL}/paper/{paper_id}/citations"
        
        params = {
            "limit": min(limit, 1000),
            "fields": "title,authors,year,venue,citationCount,externalIds",
        }
        
        try:
            response = await self.client.get(
                url, 
                params=params,
                headers=self._get_headers()
            )
            
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract citing papers from response
            citing_papers = [item.get("citingPaper", {}) for item in data.get("data", [])]
            return self._parse_results(citing_papers)
        except Exception as e:
            logger.error(f"Failed to get citations: {e}")
            return []
    
    async def get_references(self, paper_id: str, limit: int = 10) -> list[SourceResult]:
        """Get papers referenced by the given paper."""
        url = f"{self.BASE_URL}/paper/{paper_id}/references"
        
        params = {
            "limit": min(limit, 1000),
            "fields": "title,authors,year,venue,citationCount,externalIds",
        }
        
        try:
            response = await self.client.get(
                url, 
                params=params,
                headers=self._get_headers()
            )
            
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract referenced papers from response
            ref_papers = [item.get("referencedPaper", {}) for item in data.get("data", [])]
            return self._parse_results(ref_papers)
        except Exception as e:
            logger.error(f"Failed to get references: {e}")
            return []
