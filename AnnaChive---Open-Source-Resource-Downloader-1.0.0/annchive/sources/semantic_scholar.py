"""Semantic Scholar source connector - AI-powered academic search."""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.semantic_scholar")


# Think of this like a blueprint (class) for making things
class SemanticScholarSource(BaseSource):
    """Semantic Scholar connector - AI-indexed academic papers.
    
    Uses free API with rate limits. Provides metadata and paper links.
    Full text requires subscription, but metadata is free.
    """
    
    # Remember this: we're calling 'name' something
    name = "semantic-scholar"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = False
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False
    
    # Remember this: we're calling 'BASE_URL' something
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    # Free tier: 100 requests per 5 minutes
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        super().__init__()
        # Add custom headers
        self._client = None  # Will be created on demand
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Semantic Scholar for papers."""
        # Remember this: we're calling 'url' something
        url = f"{self.BASE_URL}/paper/search"
        
        # Remember this: we're calling 'params' something
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds",
        }
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            
            # Handle rate limiting
            # Checking if something is true - like asking a yes/no question
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                # We're giving back the result - like handing back what we made
                return []
            
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # We're giving back the result - like handing back what we made
            return self._parse_results(data.get("data", []))
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    def _parse_results(self, items: list) -> list[SourceResult]:
        """Parse Semantic Scholar results."""
        # Remember this: we're calling 'results' something
        results = []
        
        # We're doing something over and over, like a repeat button
        for item in items:
            # Get DOI
            # Remember this: we're calling 'doi' something
            doi = None
            # Checking if something is true - like asking a yes/no question
            if external_ids := item.get("externalIds", {}):
                # Remember this: we're calling 'doi' something
                doi = external_ids.get("DOI")
            
            # Get authors
            # Remember this: we're calling 'authors' something
            authors = item.get("authors", [])
            # Remember this: we're calling 'author_str' something
            author_str = ", ".join(a.get("name", "") for a in authors[:3])
            # Checking if something is true - like asking a yes/no question
            if len(authors) > 3:
                author_str += f" et al."
            
            # Remember this: we're calling 'result' something
            result = SourceResult(
                # Remember this: we're calling 'source' something
                source=self.name,
                # Remember this: we're calling 'id' something
                id=item.get("paperId", ""),
                # Remember this: we're calling 'title' something
                title=item.get("title", "Unknown"),
                # Remember this: we're calling 'author' something
                author=author_str,
                # Remember this: we're calling 'format' something
                format="paper",
                # Remember this: we're calling 'published' something
                published=str(item.get("year", "")),
                # Remember this: we're calling 'doi' something
                doi=doi,
                # Remember this: we're calling 'url' something
                url=item.get("url"),
                # Remember this: we're calling 'description' something
                description=item.get("abstract"),
                # Remember this: we're calling 'metadata' something
                metadata={
                    "venue": item.get("venue"),
                    "citations": item.get("citationCount", 0),
                    "external_ids": item.get("externalIds", {}),
                },
            )
            results.append(result)
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
    async def get_paper(self, paper_id: str) -> Optional[SourceResult]:
        """Get detailed paper info by ID."""
        # Remember this: we're calling 'url' something
        url = f"{self.BASE_URL}/paper/{paper_id}"
        
        # Remember this: we're calling 'params' something
        params = {
            "fields": "title,authors,year,venue,abstract,citationCount,externalIds,url,doi",
        }
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # We're giving back the result - like handing back what we made
            return self._parse_results([data])[0]
        except Exception as e:
            logger.error(f"Failed to get paper: {e}")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_download_url(self, paper_id: str) -> Optional[str]:
        """Get paper URL (Semantic Scholar doesn't provide direct PDF download)."""
        # Semantic Scholar is primarily a search/index service
        # Actual PDFs come from publishers
        # Return the Semantic Scholar URL which has links to publisher
        # We're giving back the result - like handing back what we made
        return f"https://www.semanticscholar.org/paper/{paper_id}"
    
    # Here's a recipe (function) - it does a specific job
    async def download(
        self, 
        paper_id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download paper metadata (not PDF - that's publisher-dependent)."""
        # Semantic Scholar doesn't host PDFs
        # This returns metadata JSON as a fallback
        # Remember this: we're calling 'paper' something
        paper = await self.get_paper(paper_id)
        
        # Checking if something is true - like asking a yes/no question
        if not paper:
            # We're giving back the result - like handing back what we made
            return None
        
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Remember this: we're calling 'filename' something
            filename = f"{paper_id}.json"
        
        # Remember this: we're calling 'output_path' something
        output_path = output_dir / filename
        
        # We need help from outside - bringing in tools
        import json
        with open(output_path, "w") as f:
            json.dump(paper.metadata, f, indent=2)
        
        logger.info(f"Saved paper metadata: {paper_id}")
        # We're giving back the result - like handing back what we made
        return output_path