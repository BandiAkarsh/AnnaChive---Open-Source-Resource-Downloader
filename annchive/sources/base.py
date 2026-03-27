"""Base source class for all resource connectors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from ..config import get_config
from ..tor.proxy import get_tor_client
from ..utils.logger import get_logger
# Shared constants - avoid magic numbers
from ..constants import DOWNLOAD_CHUNK_SIZE, MIN_URL_LENGTH

logger = get_logger("sources.base")


@dataclass
class SourceResult:
    """Standard result format from any source."""
    source: str
    id: str  # Unique ID (MD5, DOI, arXiv ID, etc.)
    title: str
    author: Optional[str] = None
    format: Optional[str] = None
    size: Optional[str] = None
    size_bytes: Optional[int] = None
    url: Optional[str] = None
    md5: Optional[str] = None
    doi: Optional[str] = None
    published: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None  # Extra metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def _validate_url(self, url: Optional[str]) -> Optional[str]:
        """Validate and sanitize URL from API response.
        
        Args:
            url: The URL to validate
            
        Returns:
            Validated URL or None if invalid
        """
        if not url:
            return None
        
        # Basic validation - check for valid URL format
        if not isinstance(url, str):
            logger.warning(f"Invalid URL type: {type(url)}")
            return None
        
        # Check for minimum URL structure
        url = url.strip()
        if not url or len(url) < MIN_URL_LENGTH:
            logger.warning(f"URL too short: {url}")
            return None
        
        # Ensure URL has a valid scheme
        if not url.startswith(("http://", "https://", "ftp://", "magnet:")):
            logger.warning(f"URL has invalid scheme: {url}")
            return None
        
        return url
    
    def validate_and_sanitize(self) -> "SourceResult":
        """Validate and sanitize all URLs in this result.
        
        Returns:
            Self with validated URLs
        """
        self.url = self._validate_url(self.url)
        return self


class BaseSource(ABC):
    """Base class for all source connectors.
    
    Each source must implement:
    - search(query, limit): Find resources
    - get_download_url(id): Get download URL
    - download(id, path): Download to file
    
    Security features:
    - Tor routing support for restricted sources
    - Fallback chain for failed downloads
    - No external logging
    """
    
    name: str = "base"  # Override in subclass
    requires_tor: bool = False  # Does this source require Tor?
    requires_auth: bool = False  # Does it need API key?
    
    def __init__(self):
        self.config = get_config()
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client (with Tor support if enabled)."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client based on Tor configuration."""
        if self.config.tor_enabled or self.requires_tor:
            tor_client = get_tor_client()
            return tor_client.get_client()
        
        return httpx.AsyncClient(
            timeout=self.config.timeout,
            follow_redirects=True,
        )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SourceResult]:
        """Search for resources.
        
        Args:
            query: Search query
            limit: Max results to return
        
        Returns:
            List of SourceResult objects
        """
        pass
    
    async def get_download_url(self, id: str) -> Optional[str]:
        """Get the download URL for a resource.
        
        Override in subclass if special handling needed.
        """
        return None
    
    async def download(
        self, 
        id: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download a resource.
        
        Args:
            id: Resource ID (MD5, DOI, etc.)
            output_dir: Directory to save to
            filename: Optional filename
        
        Returns:
            Path to downloaded file, or None if failed
        """
        url = await self.get_download_url(id)
        if not url:
            return None
        
        # Determine filename
        if not filename:
            filename = f"{id}.{self.name}"
        
        output_path = output_dir / filename
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=self.config.chunk_size):
                    f.write(chunk)
            
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def _parse_result(self, data: dict) -> SourceResult:
        """Parse source-specific data into SourceResult.
        
        Override in subclass for custom parsing.
        """
        return SourceResult(
            source=self.name,
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            author=data.get("author"),
            format=data.get("format"),
            size=data.get("size"),
            size_bytes=data.get("size_bytes"),
            url=data.get("url"),
            md5=data.get("md5"),
            doi=data.get("doi"),
            metadata=data,
        )