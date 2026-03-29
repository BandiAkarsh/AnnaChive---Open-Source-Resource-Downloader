"""SearXNG source connector - metasearch engine.

SearXNG is an open-source metasearch engine that can search multiple sources
including Anna's Archive, academic papers, GitHub, and more.

No API key required for basic usage.

NOTE: Public SearXNG instances are frequently rate-limited or blocked by search
providers (Google, Bing, etc.). For reliable usage, consider running your own
SearXNG instance or using the ANNCHIVE_SEARXNG_URL environment variable to
set a custom instance.
"""
import os
from typing import Optional

import httpx

from .base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("sources.searxng")


# Public SearXNG instances (verified working at some point)
# These are frequently rate-limited. For reliable usage, host your own instance.
# Configure custom instance: ANNCHIVE_SEARXNG_URL env var or `annchive config set searxng_url <url>`
SEARXNG_INSTANCES = [
    "https://searx.work",
    "https://search.inetol.net",
    "https://search.privacyredirect.com",
    "https://searx.be",
    "https://searxng.eu",
    "https://searx.duckduckgo.icu",
    "https://search.bus-hit.me",
    "https://searx.com",
]


class SearXNGSource(BaseSource):
    """SearXNG metasearch connector.
    
    Searches multiple sources via SearXNG instances.
    Good for: General academic search, Anna's Archive, books, papers.
    
    Note: Results depend on the SearXNG instance configuration.
    Some instances may have Anna's Archive enabled.
    
    Public instances are frequently rate-limited. For reliable usage:
    - Set custom instance via: ANNCHIVE_SEARXNG_URL env var
    - Or: annchive config set searxng_url <your-instance-url>
    - Or run your own SearXNG instance
    """
    
    name = "searxng"
    requires_tor = False
    requires_auth = False
    
    def __init__(self):
        super().__init__()
        self.base_url = self._find_working_instance()
    
    def _find_working_instance(self) -> str:
        """Find a working SearXNG instance."""
        # Priority: config file > environment variable > defaults
        from ..config import get_config
        config = get_config()
        
        # Check config first
        if config.searxng_url:
            return config.searxng_url
        
        # Check environment
        custom = os.getenv("ANNCHIVE_SEARXNG_URL")
        if custom:
            return custom
        
        # Default to first one (will test in search)
        return SEARXNG_INSTANCES[0]
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search via SearXNG."""
        try:
            # Use JSON format for easier parsing
            url = f"{self.base_url}/search"
            params = {
                "q": query,
                "format": "json",
                "engines": "annasarchive,arxiv,github,pubmed",  # Preferred engines
                "language": "en",
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_results(data.get("results", []), limit)
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"SearXNG HTTP error: {e.response.status_code}")
            # Try fallback instances
            return await self._search_with_fallback(query, limit)
        except Exception as e:
            logger.error(f"SearXNG search failed: {e}")
            return await self._search_with_fallback(query, limit)
    
    async def _search_with_fallback(self, query: str, limit: int) -> list[SourceResult]:
        """Try other SearXNG instances."""
        for instance in SEARXNG_INSTANCES:
            if instance == self.base_url:
                continue
            try:
                self.base_url = instance
                url = f"{self.base_url}/search"
                params = {
                    "q": query,
                    "format": "json",
                    "language": "en",
                }
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return self._parse_results(data.get("results", []), limit)
            except Exception:
                continue
        
        logger.warning("All SearXNG instances failed")
        return []
    
    def _parse_results(self, results: list, limit: int) -> list[SourceResult]:
        """Parse SearXNG results into SourceResult objects."""
        output = []
        
        for item in results[:limit]:
            # Determine source from URL
            url = item.get("url", "")
            source = self._detect_source(url)
            
            # Extract metadata
            title = item.get("title", "Unknown")
            author = item.get("author")
            content = item.get("content", "")
            published = item.get("published")
            
            # Determine format
            fmt = self._detect_format(url, item.get("type", ""))
            
            result = SourceResult(
                source=source,
                id=item.get("id", ""),
                title=title,
                author=author,
                format=fmt,
                url=url,
                description=content,
                published=published,
                metadata={
                    "engine": item.get("engine", ""),
                    "score": item.get("score", 0),
                    "searxng_source": self.base_url,
                },
            )
            output.append(result)
        
        return output
    
    def _detect_source(self, url: str) -> str:
        """Detect the original source from URL."""
        url_lower = url.lower()
        
        if "arxiv.org" in url_lower:
            return "arxiv"
        elif "github.com" in url_lower:
            return "github"
        elif "pubmed" in url_lower:
            return "pubmed"
        elif "annas-archive" in url_lower:
            return "annas-archive"
        elif "semanticscholar" in url_lower:
            return "semantic-scholar"
        elif "ncbi.nlm.nih.gov" in url_lower:
            return "pubmed"
        else:
            return "searxng"
    
    def _detect_format(self, url: str, content_type: str) -> str:
        """Detect file format from URL and content type."""
        url_lower = url.lower()
        
        if ".pdf" in url_lower or content_type == "application/pdf":
            return "pdf"
        elif ".epub" in url_lower:
            return "epub"
        elif ".djvu" in url_lower:
            return "djvu"
        elif ".mobi" in url_lower:
            return "mobi"
        elif content_type == "application/x-msdownload":
            return "exe"
        elif "github.com" in url_lower:
            return "repository"
        else:
            return "web"
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get download URL - SearXNG is just search, not download."""
        return None
    
    async def download(
        self, 
        id: str, 
        output_dir: "Path",
        filename: Optional[str] = None
    ) -> Optional["Path"]:
        """Download not supported - use source-specific download commands."""
        logger.info("Use source-specific download commands (e.g., annchive get arxiv)")
        return None
