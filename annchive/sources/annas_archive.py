"""Anna's Archive source connector.

Supports:
- Public search (via web scraping / search endpoint)
- Fast download API (requires membership key - see below)
- BitTorrent downloads (no key required)

Note: Anna's Archive frequently changes domains due to takedowns.
Current working domain: annas-archive.gl

To get an API key for fast downloads:
1. Go to https://annas-archive.org/donate
2. Make a donation to become a member
3. Find your API key in account settings
4. Set it with: annchive config apikey set annas-archive YOUR-KEY
"""

from pathlib import Path
from typing import Optional

import httpx
import keyring

from .base import BaseSource, SourceResult
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("sources.annas_archive")


def _get_annas_key() -> Optional[str]:
    """Get Anna's Archive API key from environment or keyring."""
    import os
    # First try environment variable
    key = os.getenv("ANNCHIVE_ANNAS_KEY")
    if key:
        return key
    # Then try keyring
    try:
        key = keyring.get_password("annchive", "annchive_annas_key")
        if key:
            return key
    except Exception:
        pass
    return None


class AnnaSource(BaseSource):
    """Anna's Archive connector.
    
    Search is public. Downloads require:
    - API key from membership (set via: annchive config apikey set annas-archive YOUR-KEY)
    - Or use BitTorrent (no key required)
    
    Domain: annas-archive.gl (currently working as of March 2026)
    Check https://annasarchive.org for current domain status.
    """
    
    name = "annas-archive"
    requires_tor = False
    requires_auth = False  # Search is free
    
    # Current working mirrors (updated March 2026)
    # Note: Anna's Archive frequently changes domains due to takedowns
    # Check https://annasarchive.org for current domains
    MIRRORS = [
        "https://annas-archive.gl",
    ]
    
    def __init__(self):
        super().__init__()
        self.base_url = self.MIRRORS[0]
        # Load API key from environment or keyring
        self._api_key = _get_annas_key()
    
    def _get_search_url(self) -> str:
        """Get search endpoint URL."""
        return f"{self.base_url}/search"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Anna's Archive.
        
        Args:
            query: Search query (title, author, ISBN, MD5)
            limit: Max results
        
        Returns:
            List of SourceResult objects
        """
        results = await self._search_with_mirrors(query, limit)
        return results
    
    async def _search_with_mirrors(self, query: str, limit: int) -> list[SourceResult]:
        """Try searching with each mirror in order."""
        errors = []
        for mirror in self.MIRRORS:
            self.base_url = mirror
            try:
                results = await self._search_impl(query, limit)
                if results:
                    return results
            except Exception as e:
                errors.append(f"{mirror}: {e}")
                continue
        
        # All mirrors failed - log helpful message
        logger.warning("Anna's Archive: All mirrors failed or are down")
        logger.info("Anna's Archive domains frequently change due to takedowns.")
        logger.info("Check current status at: https://annasarchive.org")
        logger.info("Alternatives: Use SearXNG or set up local annas-mcp server")
        
        return []
    
    async def _search_impl(self, query: str, limit: int) -> list[SourceResult]:
        """Internal search implementation - scrapes search page."""
        url = self._get_search_url()
        params = {"q": query}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            # Parse HTML response for results
            return self._parse_html(response.text, limit)
        except httpx.HTTPStatusError as e:
            logger.warning(f"Anna's Archive search failed: HTTP {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Anna's Archive search error: {e}")
            return []
    
    def _parse_html(self, html: str, limit: int) -> list[SourceResult]:
        """Parse search results from HTML."""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Find search result items
            # Anna's Archive uses specific CSS classes for results
            items = soup.select("div.flex.flex-col.gap-2")[:limit]
            
            for item in items:
                # Extract title
                title_elem = item.select_one("a[href*='/book/'], a[href*='/paper/']")
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                href = title_elem.get("href", "")
                
                # Extract author
                author_elem = item.select_one("span.text-gray-400, .text-gray-500")
                author = author_elem.get_text(strip=True) if author_elem else None
                
                # Extract format/size
                meta_elem = item.select_one("span.text-xs")
                size = None
                if meta_elem:
                    meta_text = meta_elem.get_text(strip=True)
                    if "MB" in meta_text or "GB" in meta_text:
                        size = meta_text
                
                # Extract MD5 from URL if available
                md5 = None
                if "/book/" in href:
                    # Try to extract ID
                    parts = href.rstrip("/").split("/")
                    if parts:
                        md5 = parts[-1]
                
                result = SourceResult(
                    source=self.name,
                    id=md5 or "",
                    title=title,
                    author=author,
                    format="ebook",  # Default format
                    size=size,
                    url=f"{self.base_url}{href}" if href.startswith("/") else href,
                    md5=md5,
                )
                results.append(result)
                
        except ImportError:
            logger.error("BeautifulSoup not installed: pip install beautifulsoup4")
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
        
        return results
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get download URL for a resource.
        
        Uses fast_download API if API key is set, otherwise returns None.
        """
        if not self._api_key:
            logger.info("No ANNCHIVE_ANNAS_KEY set - download not available")
            return None
        
        url = f"{self.base_url}/dyn/api/fast_download.json"
        
        try:
            response = await self.client.get(
                url,
                params={"id": id},
                headers={"x-api-key": self._api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("downloadUrl")
            else:
                logger.warning(f"Fast download API returned: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Failed to get download URL: {e}")
            return None
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download via fast_download API or BitTorrent."""
        # Try fast download first
        download_url = await self.get_download_url(id)
        
        if download_url:
            # Download the file
            from ..storage.downloader import DownloadManager
            dm = DownloadManager()
            success = await dm.download(download_url, output_dir, filename=filename)
            if success:
                return output_dir / (filename or id)
        
        # Fallback: return magnet link info
        logger.info(f"Download requires ANNCHIVE_ANNAS_KEY or use BitTorrent")
        return None
    
    def get_magnet_link(self, info_hash: str, filename: str) -> str:
        """Generate a magnet link for BitTorrent download."""
        return f"magnet:?xt=urn:btih:{info_hash}&dn={filename}"
    
    async def get_torrent_info(self, md5: str) -> dict:
        """Get torrent information for a file."""
        url = f"{self.base_url}/dyn/torrent"
        params = {"md5": md5}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get torrent info: {e}")
            return {}
    
    async def find_alternatives(self, md5: str) -> list[dict]:
        """Find alternative download sources for a file."""
        url = f"{self.base_url}/dyn/metadata"
        params = {"md5": md5}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("files", [])
        except Exception:
            return []
