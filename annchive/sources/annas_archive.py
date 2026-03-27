"""Anna's Archive source connector.

Supports:
- Public search API (no donation required)
- BitTorrent download (no donation required)  
- Mirror fallback
- Tor routing for onion mirrors

Based on reverse-engineered API endpoints.
"""
from pathlib import Path
from typing import Optional

import httpx

from .base import BaseSource, SourceResult
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("sources.annas_archive")


class AnnaSource(BaseSource):
    """Anna's Archive connector.
    
    Uses public search endpoints. Download requires:
    1. BitTorrent (public, no auth)
    2. Mirror URLs (fallback)
    3. Tor/onion mirrors (if enabled)
    """
    
    name = "annas-archive"
    requires_tor = False  # Can work without Tor
    requires_auth = False  # Search is free
    
    # Known mirrors (Anna's Archive has multiple)
    MIRRORS = [
        "https://annas-archive.li",
        "https://annas-archive.pm", 
        "https://annas-archive.in",
    ]
    
    # Onion mirrors (require Tor)
    ONION_MIRRORS = [
        # Placeholder - actual onion addresses change
    ]
    
    def __init__(self):
        super().__init__()
        self.base_url = self.MIRRORS[0]  # Default to first mirror
    
    def _get_search_url(self) -> str:
        """Get search endpoint URL."""
        return f"{self.base_url}/dyn/searchn"
    
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Anna's Archive.
        
        Args:
            query: Search query (title, author, ISBN, MD5)
            limit: Max results
        
        Returns:
            List of SourceResult objects
        """
        results = []
        
        # Try each mirror
        for mirror in self.MIRRORS:
            self.base_url = mirror
            try:
                results = await self._search_impl(query, limit)
                if results:
                    break  # Found results, stop trying mirrors
            except Exception as e:
                logger.warning(f"Mirror {mirror} failed: {e}")
                continue
        
        # If no results and Tor enabled, try onion mirrors
        if not results and self.config.tor_enabled:
            results = await self._search_onion(query, limit)
        
        return results
    
    async def _search_impl(self, query: str, limit: int) -> list[SourceResult]:
        """Internal search implementation."""
        # Anna's Archive search endpoint
        url = self._get_search_url()
        
        # Build search params
        # Note: Exact API params may vary - this is based on reverse engineering
        params = {
            "q": query,
            "limit": limit,
            "offset": 0,
            "sort": "relevance",
            "type": "books",  # books, articles, journals
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data)
        except httpx.HTTPStatusError as e:
            logger.warning(f"Search failed: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def _search_onion(self, query: str, limit: int) -> list[SourceResult]:
        """Search via onion mirrors (requires Tor)."""
        # For now, return empty - onion addresses change frequently
        # User can manually add via config
        return []
    
    def _parse_results(self, data: dict) -> list[SourceResult]:
        """Parse Anna's Archive response into SourceResult objects."""
        results = []
        
        # Response format may vary - handle both formats
        items = data.get("results", data)
        
        if not isinstance(items, list):
            items = [items]
        
        for item in items:
            result = SourceResult(
                source=self.name,
                id=item.get("md5", item.get("id", "")),
                title=item.get("title", "Unknown"),
                author=item.get("author"),
                format=item.get("format"),
                size=item.get("size"),
                size_bytes=item.get("size_bytes"),
                md5=item.get("md5"),
                url=item.get("url"),
                metadata=item,
            )
            results.append(result)
        
        return results
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get download URL for a resource.
        
        Uses fallback chain:
        1. Direct CDN URL from search result
        2. BitTorrent info hash
        3. Mirror URL construction
        """
        # First check if we have cached URL from search
        # The id is typically the MD5 hash
        
        # Try to get from search result metadata
        # In practice, the search returns URLs in the response
        
        # Fallback: construct URL (this may not work without donation)
        # Anna's Archive requires donation for direct download API
        
        # Best approach: use BitTorrent
        # Return the magnet link or torrent info
        
        # For now, return None - actual implementation requires
        # more complex logic to get download URLs from metadata
        return None
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download via BitTorrent (no donation required).
        
        Uses the public torrent files from Anna's Archive.
        """
        # This would integrate with a BitTorrent client
        # For now, return None - implement in Phase 2
        
        # TODO: Integrate with libtorrent for bittorrent download
        logger.info(f"BitTorrent download not yet implemented for {id}")
        return None
    
    async def get_torrent_info(self, md5: str) -> dict:
        """Get torrent information for a file.
        
        Anna's Archive provides torrent metadata publicly.
        This allows download without donation.
        """
        # Query the torrent metadata endpoint
        url = f"{self.base_url}/dyn/torrent"
        params = {"md5": md5}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get torrent info: {e}")
            return {}
    
    def get_magnet_link(self, info_hash: str, filename: str) -> str:
        """Generate a magnet link for BitTorrent download."""
        return f"magnet:?xt=urn:btih:{info_hash}&dn={filename}"
    
    async def find_alternatives(self, md5: str) -> list[dict]:
        """Find alternative download sources for a file.
        
        Anna's Archive often has multiple copies in different torrents.
        """
        # Query metadata for all copies
        url = f"{self.base_url}/dyn/metadata"
        params = {"md5": md5}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("files", [])
        except Exception:
            return []