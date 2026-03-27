"""Anna's Archive source connector.

Supports:
- Public search API (no donation required)
- BitTorrent download (no donation required)  
- Mirror fallback
- Tor routing for onion mirrors

Based on reverse-engineered API endpoints.
"""
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We need help from outside - bringing in tools
import httpx

# We're bringing in tools from another file
from .base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..config import get_config
# We're bringing in tools from another file
from ..utils.logger import get_logger

# Remember this: we're calling 'logger' something
logger = get_logger("sources.annas_archive")


# Think of this like a blueprint (class) for making things
class AnnaSource(BaseSource):
    """Anna's Archive connector.
    
    Uses public search endpoints. Download requires:
    1. BitTorrent (public, no auth)
    2. Mirror URLs (fallback)
    3. Tor/onion mirrors (if enabled)
    """
    
    # Remember this: we're calling 'name' something
    name = "annas-archive"
    # Remember this: we're calling 'requires_tor' something
    requires_tor = False  # Can work without Tor
    # Remember this: we're calling 'requires_auth' something
    requires_auth = False  # Search is free
    
    # Known mirrors (Anna's Archive has multiple)
    # Remember this: we're calling 'MIRRORS' something
    MIRRORS = [
        "https://annas-archive.li",
        "https://annas-archive.pm", 
        "https://annas-archive.in",
    ]
    
    # Onion mirrors (require Tor)
    # Remember this: we're calling 'ONION_MIRRORS' something
    ONION_MIRRORS = [
        # Placeholder - actual onion addresses change
    ]
    
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        super().__init__()
        self.base_url = self.MIRRORS[0]  # Default to first mirror
    
    # Here's a recipe (function) - it does a specific job
    def _get_search_url(self) -> str:
        """Get search endpoint URL."""
        # We're giving back the result - like handing back what we made
        return f"{self.base_url}/dyn/searchn"
    
    # Here's a recipe (function) - it does a specific job
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search Anna's Archive.
        
        Args:
            query: Search query (title, author, ISBN, MD5)
            limit: Max results
        
        Returns:
            List of SourceResult objects
        """
        # Remember this: we're calling 'results' something
        results = []
        
        # Try each mirror
        # We're doing something over and over, like a repeat button
        for mirror in self.MIRRORS:
            self.base_url = mirror
            # We're trying something that might go wrong
            try:
                # Remember this: we're calling 'results' something
                results = await self._search_impl(query, limit)
                # Checking if something is true - like asking a yes/no question
                if results:
                    break  # Found results, stop trying mirrors
            except Exception as e:
                logger.warning(f"Mirror {mirror} failed: {e}")
                continue
        
        # If no results and Tor enabled, try onion mirrors
        # Checking if something is true - like asking a yes/no question
        if not results and self.config.tor_enabled:
            # Remember this: we're calling 'results' something
            results = await self._search_onion(query, limit)
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
    async def _search_impl(self, query: str, limit: int) -> list[SourceResult]:
        """Internal search implementation."""
        # Anna's Archive search endpoint
        # Remember this: we're calling 'url' something
        url = self._get_search_url()
        
        # Build search params
        # Note: Exact API params may vary - this is based on reverse engineering
        # Remember this: we're calling 'params' something
        params = {
            "q": query,
            "limit": limit,
            "offset": 0,
            "sort": "relevance",
            "type": "books",  # books, articles, journals
        }
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            
            # We're giving back the result - like handing back what we made
            return self._parse_results(data)
        except httpx.HTTPStatusError as e:
            logger.warning(f"Search failed: {e.response.status_code}")
            # We're giving back the result - like handing back what we made
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            # We're giving back the result - like handing back what we made
            return []
    
    # Here's a recipe (function) - it does a specific job
    async def _search_onion(self, query: str, limit: int) -> list[SourceResult]:
        """Search via onion mirrors (requires Tor)."""
        # For now, return empty - onion addresses change frequently
        # User can manually add via config
        # We're giving back the result - like handing back what we made
        return []
    
    # Here's a recipe (function) - it does a specific job
    def _parse_results(self, data: dict) -> list[SourceResult]:
        """Parse Anna's Archive response into SourceResult objects."""
        # Remember this: we're calling 'results' something
        results = []
        
        # Response format may vary - handle both formats
        # Remember this: we're calling 'items' something
        items = data.get("results", data)
        
        # Checking if something is true - like asking a yes/no question
        if not isinstance(items, list):
            # Remember this: we're calling 'items' something
            items = [items]
        
        # We're doing something over and over, like a repeat button
        for item in items:
            # Remember this: we're calling 'result' something
            result = SourceResult(
                # Remember this: we're calling 'source' something
                source=self.name,
                # Remember this: we're calling 'id' something
                id=item.get("md5", item.get("id", "")),
                # Remember this: we're calling 'title' something
                title=item.get("title", "Unknown"),
                # Remember this: we're calling 'author' something
                author=item.get("author"),
                # Remember this: we're calling 'format' something
                format=item.get("format"),
                # Remember this: we're calling 'size' something
                size=item.get("size"),
                # Remember this: we're calling 'size_bytes' something
                size_bytes=item.get("size_bytes"),
                # Remember this: we're calling 'md5' something
                md5=item.get("md5"),
                # Remember this: we're calling 'url' something
                url=item.get("url"),
                # Remember this: we're calling 'metadata' something
                metadata=item,
            )
            results.append(result)
        
        # We're giving back the result - like handing back what we made
        return results
    
    # Here's a recipe (function) - it does a specific job
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
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
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
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_torrent_info(self, md5: str) -> dict:
        """Get torrent information for a file.
        
        Anna's Archive provides torrent metadata publicly.
        This allows download without donation.
        """
        # Query the torrent metadata endpoint
        # Remember this: we're calling 'url' something
        url = f"{self.base_url}/dyn/torrent"
        # Remember this: we're calling 'params' something
        params = {"md5": md5}
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # We're giving back the result - like handing back what we made
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get torrent info: {e}")
            # We're giving back the result - like handing back what we made
            return {}
    
    # Here's a recipe (function) - it does a specific job
    def get_magnet_link(self, info_hash: str, filename: str) -> str:
        """Generate a magnet link for BitTorrent download."""
        # We're giving back the result - like handing back what we made
        return f"magnet:?xt=urn:btih:{info_hash}&dn={filename}"
    
    # Here's a recipe (function) - it does a specific job
    async def find_alternatives(self, md5: str) -> list[dict]:
        """Find alternative download sources for a file.
        
        Anna's Archive often has multiple copies in different torrents.
        """
        # Query metadata for all copies
        # Remember this: we're calling 'url' something
        url = f"{self.base_url}/dyn/metadata"
        # Remember this: we're calling 'params' something
        params = {"md5": md5}
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Remember this: we're calling 'data' something
            data = response.json()
            # We're giving back the result - like handing back what we made
            return data.get("files", [])
        except Exception:
            # We're giving back the result - like handing back what we made
            return []