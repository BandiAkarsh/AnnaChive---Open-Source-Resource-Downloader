"""Semantic Scholar source connector - AI-powered academic search."""
from pathlib import Path
from typing import Optional

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.semantic_scholar")


class SemanticScholarSource(BaseSource):
    """Semantic Scholar connector - AI-indexed academic papers.
    
    Uses free API with rate limits. Provides metadata and paper links.
    Full text requires subscription, but metadata is free.
    """
    
    name = "semantic-scholar"
    requires_tor = False
    requires_auth = False
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    # Free tier: 100 requests per 5 minutes
    def __init__(self):
        super().__init__()
        # Add custom headers
        self._client = None  # Will be created on demand
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Semantic Scholar for papers."""
        url = f"{self.BASE_URL}/paper/search"
        
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds",
        }
        
        try:
            response = await self.client.get(url, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data.get("data", []))
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse Semantic Scholar results."""
        results = []
        
        for item in items:
            # Get DOI
            doi = None
            if external_ids := item.get("externalIds", {}):
                doi = external_ids.get("DOI")
            
            # Get authors
            authors = item.get("authors", [])
            author_str = ", ".join(a.get("name", "") for a in authors[:3])
            if len(authors) > 3:
                author_str += f" et al."
            
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
        """Get detailed paper info by ID."""
        url = f"{self.BASE_URL}/paper/{paper_id}"
        
        params = {
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,url,doi",
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results([data])[0]
        except Exception as e:
            logger.error(f"Failed to get paper: {e}")
            return None
    
    async def get_download_url(self, paper_id: str) -> Optional[str]:
        """Get paper URL (Semantic Scholar doesn't provide direct PDF download)."""
        # Semantic Scholar is primarily a search/index service
        # Actual PDFs come from publishers
        # Return the Semantic Scholar URL which has links to publisher
        return f"https://www.semanticscholar.org/paper/{paper_id}"
    
    async def download(
        self, 
        paper_id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download paper metadata (not PDF - that's publisher-dependent)."""
        # Semantic Scholar doesn't host PDFs
        # This returns metadata JSON as a fallback
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