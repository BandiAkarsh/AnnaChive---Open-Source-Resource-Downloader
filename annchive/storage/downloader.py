"""Download manager with fallback chain logic."""
# We need help from outside - bringing in tools
import asyncio
# We're bringing in tools from another file
from dataclasses import dataclass
# We're bringing in tools from another file
from enum import Enum
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We need help from outside - bringing in tools
import httpx
# We're bringing in tools from another file
from tqdm import tqdm

# We're bringing in tools from another file
from ..config import get_config
# We're bringing in tools from another file
from ..sources.base import BaseSource, SourceResult
# We're bringing in tools from another file
from ..utils.logger import get_logger
# Shared constants - avoid magic numbers
from ..constants import TITLE_TRUNCATE_LENGTH, DOWNLOAD_CHUNK_SIZE, SAFE_FILENAME_CHARS

# Remember this: we're calling 'logger' something
logger = get_logger("storage.downloader")


# Think of this like a blueprint (class) for making things
class DownloadMethod(Enum):
    """Download method used."""
    # Remember this: we're calling 'DIRECT' something
    DIRECT = "direct"
    # Remember this: we're calling 'TOR' something
    TOR = "tor"
    # Remember this: we're calling 'TORRENT' something
    TORRENT = "torrent"
    # Remember this: we're calling 'MIRROR' something
    MIRROR = "mirror"
    # Remember this: we're calling 'FALLBACK' something
    FALLBACK = "fallback"


@dataclass
# Think of this like a blueprint (class) for making things
class DownloadResult:
    """Result of a download attempt."""
    success: bool
    path: Optional[Path] = None
    method: Optional[DownloadMethod] = None
    error: Optional[str] = None
    attempts: int = 0


# Think of this like a blueprint (class) for making things
class DownloadManager:
    """Manages downloads with automatic fallback.
    
    For each source, tries in order:
    1. Direct (no Tor)
    2. Via Tor (if enabled)
    3. Via torrent (for Anna's Archive)
    4. Via mirrors
    """
    
    # Here's a recipe (function) - it does a specific job
    def __init__(self, config=None):
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    # Here's a recipe (function) - it does a specific job
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        # Checking if something is true - like asking a yes/no question
        if self._client is None:
            self._client = httpx.AsyncClient(
                # Remember this: we're calling 'timeout' something
                timeout=self.config.timeout,
                # Remember this: we're calling 'follow_redirects' something
                follow_redirects=True,
            )
        # We're giving back the result - like handing back what we made
        return self._client
    
    # Here's a recipe (function) - it does a specific job
    async def download_with_fallback(
        self,
        source: BaseSource,
        item: SourceResult,
        output_dir: Path,
        filename: Optional[str] = None
    ) -> bool:
        """Download with automatic fallback chain.
        
        Returns True if download succeeded, False otherwise.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Checking if something is true - like asking a yes/no question
        if not filename:
            # Generate filename from title or ID
            # Remember this: we're calling 'safe_title' something
            safe_title = "".join(c for c in item.title[:TITLE_TRUNCATE_LENGTH] 
                                 if c.isalnum() or c in SAFE_FILENAME_CHARS)
            # Remember this: we're calling 'ext' something
            ext = item.format or "bin"
            # Remember this: we're calling 'filename' something
            filename = f"{safe_title}.{ext}"
        
        # Remember this: we're calling 'output_path' something
        output_path = output_dir / filename
        
        # Validate path to prevent path traversal attacks
        output_path = output_path.resolve()
        output_dir = output_dir.resolve()
        if not str(output_path).startswith(str(output_dir)):
            logger.error(f"Path traversal detected: {output_path}")
            return False
        
        # Try each method in order
        # Remember this: we're calling 'methods' something
        methods = self._get_methods(source)
        
        # We're doing something over and over, like a repeat button
        for method in methods:
            # Remember this: we're calling 'result' something
            result = await self._try_download(
                source, item, output_path, method
            )
            
            # Checking if something is true - like asking a yes/no question
            if result.success:
                logger.info(f"Downloaded via {result.method.value}: {item.title}")
                # Ensure client is closed after successful download
                await self.close()
                # We're giving back the result - like handing back what we made
                return True
            
            logger.debug(f"Method {method.value} failed: {result.error}")
        
        logger.error(f"All methods failed for: {item.title}")
        # Ensure client is closed even on failure
        await self.close()
        # We're giving back the result - like handing back what we made
        return False
    
    # Here's a recipe (function) - it does a specific job
    def _get_methods(self, source: BaseSource) -> list[DownloadMethod]:
        """Determine which methods to try based on source and config."""
        # Remember this: we're calling 'methods' something
        methods = [DownloadMethod.DIRECT]
        
        # If Tor is enabled or source requires Tor, add Tor method
        # Checking if something is true - like asking a yes/no question
        if self.config.tor_enabled or source.requires_tor:
            methods.append(DownloadMethod.TOR)
        
        # Add torrent for Anna's Archive
        # Checking if something is true - like asking a yes/no question
        if source.name == "annas-archive":
            methods.append(DownloadMethod.TORRENT)
        
        # Add mirror fallback
        methods.append(DownloadMethod.MIRROR)
        
        # We're giving back the result - like handing back what we made
        return methods
    
    # Here's a recipe (function) - it does a specific job
    async def _try_download(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path,
        method: DownloadMethod
    ) -> DownloadResult:
        """Try a specific download method."""
        # We're trying something that might go wrong
        try:
            # Checking if something is true - like asking a yes/no question
            if method == DownloadMethod.DIRECT:
                # We're giving back the result - like handing back what we made
                return await self._download_direct(source, item, output_path)
            
            # If the first answer was no, try this instead
            elif method == DownloadMethod.TOR:
                # We're giving back the result - like handing back what we made
                return await self._download_tor(source, item, output_path)
            
            # If the first answer was no, try this instead
            elif method == DownloadMethod.TORRENT:
                # We're giving back the result - like handing back what we made
                return await self._download_torrent(source, item, output_path)
            
            # If the first answer was no, try this instead
            elif method == DownloadMethod.MIRROR:
                # We're giving back the result - like handing back what we made
                return await self._download_mirror(source, item, output_path)
        
        except Exception as e:
            # We're giving back the result - like handing back what we made
            return DownloadResult(success=False, error=str(e), method=method)
    
    # Here's a recipe (function) - it does a specific job
    async def _download_direct(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Direct download without Tor."""
        # Remember this: we're calling 'url' something
        url = item.url or await source.get_download_url(item.id)
        
        # Checking if something is true - like asking a yes/no question
        if not url:
            # We're giving back the result - like handing back what we made
            return DownloadResult(success=False, error="No URL available")
        
        # We're giving back the result - like handing back what we made
        return await self._download_file(url, output_path, DownloadMethod.DIRECT)
    
    # Here's a recipe (function) - it does a specific job
    async def _download_tor(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Download via Tor proxy."""
        # We're bringing in tools from another file
        from ..tor.proxy import get_tor_client
        
        # Remember this: we're calling 'tor_client' something
        tor_client = get_tor_client(self.config.tor_port)
        # Remember this: we're calling 'client' something
        client = tor_client.get_client()
        
        # Remember this: we're calling 'url' something
        url = item.url or await source.get_download_url(item.id)
        
        # Checking if something is true - like asking a yes/no question
        if not url:
            # We're giving back the result - like handing back what we made
            return DownloadResult(success=False, error="No URL available")
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'response' something
            response = await client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                # We're doing something over and over, like a repeat button
                async for chunk in response.aiter_bytes(chunk_size=self.config.chunk_size):
                    f.write(chunk)
            
            # We're giving back the result - like handing back what we made
            return DownloadResult(success=True, path=output_path, method=DownloadMethod.TOR)
        
        except Exception as e:
            # We're giving back the result - like handing back what we made
            return DownloadResult(success=False, error=str(e), method=DownloadMethod.TOR)
    
    # Here's a recipe (function) - it does a specific job
    async def _download_torrent(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Download via BitTorrent (for Anna's Archive).
        
        This would integrate with libtorrent.
        Currently returns False - implement in Phase 2.
        """
        # TODO: Implement BitTorrent download
        # - Get torrent info from Anna's Archive metadata
        # - Use libtorrent to download specific files
        # - Save to output_path
        
        # We're giving back the result - like handing back what we made
        return DownloadResult(
            # Remember this: we're calling 'success' something
            success=False, 
            # Remember this: we're calling 'error' something
            error="BitTorrent download not yet implemented",
            # Remember this: we're calling 'method' something
            method=DownloadMethod.TORRENT
        )
    
    # Here's a recipe (function) - it does a specific job
    async def _download_mirror(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Try alternative mirrors."""
        # For sources that have mirrors (like Anna's Archive)
        # Try alternative base URLs
        
        # Checking if something is true - like asking a yes/no question
        if source.name == "annas-archive":
            # We're bringing in tools from another file
            from ..sources.annas_archive import AnnaSource
            
            # Try alternate mirrors
        # Remember this: we're calling 'mirrors' something
        mirrors = AnnaSource.MIRRORS[1:]  # Skip first (already tried)
        
        # We're doing something over and over, like a repeat button
        for mirror in mirrors:
            result = await self._try_mirror(source, item, output_path, mirror)
            if result and result.success:
                return result
        
        # We're giving back the result - like handing back what we made
        return DownloadResult(success=False, error="No mirrors available")
    
    async def _try_mirror(self, source, item, output_path, mirror):
        """Try downloading from a specific mirror."""
        from ..sources.annas_archive import AnnaSource
        
        try:
            # Temporarily change base URL
            old_url = source.base_url
            source.base_url = mirror
            
            url = await source.get_download_url(item.id)
            if not url:
                source.base_url = old_url
                return None
            
            result = await self._download_file(url, output_path, DownloadMethod.MIRROR)
            source.base_url = old_url
            
            if result.success:
                return result
            
            source.base_url = old_url
        except Exception as e:
            logger.warning(f"Mirror {mirror} failed: {e}")
            source.base_url = old_url
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def _download_file(
        self,
        url: str,
        output_path: Path,
        method: DownloadMethod
    ) -> DownloadResult:
        """Download a file from URL."""
        return await self._download_with_progress(url, output_path, method) \
            if self._has_content_length(url) \
            else await self._download_simple(url, output_path, method)
    
    async def _has_content_length(self, url: str) -> bool:
        """Check if response will have content-length header."""
        return True  # Most servers provide this
    
    async def _download_simple(
        self, url: str, output_path: Path, method: DownloadMethod
    ) -> DownloadResult:
        """Download without progress (fallback)."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
            
            return DownloadResult(success=True, path=output_path, method=method)
        except httpx.HTTPStatusError as e:
            return DownloadResult(success=False, error=f"HTTP {e.response.status_code}", method=method)
        except Exception as e:
            return DownloadResult(success=False, error=str(e), method=method)
    
    async def _download_with_progress(
        self, url: str, output_path: Path, method: DownloadMethod
    ) -> DownloadResult:
        """Download with progress bar."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            
            with open(output_path, "wb") as f, tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=output_path.name
            ) as pbar:
                async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
                    pbar.update(len(chunk))
            
            return DownloadResult(success=True, path=output_path, method=method)
        except httpx.HTTPStatusError as e:
            return DownloadResult(success=False, error=f"HTTP {e.response.status_code}", method=method)
        except Exception as e:
            return DownloadResult(success=False, error=str(e), method=method)
    
    # Here's a recipe (function) - it does a specific job
    async def close(self):
        """Close HTTP client."""
        # Checking if something is true - like asking a yes/no question
        if self._client:
            await self._client.aclose()
            self._client = None