"""Download manager with fallback chain logic."""
import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from tqdm import tqdm

from ..config import get_config
from ..sources.base import BaseSource, SourceResult
from ..utils.logger import get_logger

logger = get_logger("storage.downloader")


class DownloadMethod(Enum):
    """Download method used."""
    DIRECT = "direct"
    TOR = "tor"
    TORRENT = "torrent"
    MIRROR = "mirror"
    FALLBACK = "fallback"


@dataclass
class DownloadResult:
    """Result of a download attempt."""
    success: bool
    path: Optional[Path] = None
    method: Optional[DownloadMethod] = None
    error: Optional[str] = None
    attempts: int = 0


class DownloadManager:
    """Manages downloads with automatic fallback.
    
    For each source, tries in order:
    1. Direct (no Tor)
    2. Via Tor (if enabled)
    3. Via torrent (for Anna's Archive)
    4. Via mirrors
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                follow_redirects=True,
            )
        return self._client
    
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
        
        if not filename:
            # Generate filename from title or ID
            safe_title = "".join(c for c in item.title[:50] if c.isalnum() or c in " -_")
            ext = item.format or "bin"
            filename = f"{safe_title}.{ext}"
        
        output_path = output_dir / filename
        
        # Try each method in order
        methods = self._get_methods(source)
        
        for method in methods:
            result = await self._try_download(
                source, item, output_path, method
            )
            
            if result.success:
                logger.info(f"Downloaded via {result.method.value}: {item.title}")
                return True
            
            logger.debug(f"Method {method.value} failed: {result.error}")
        
        logger.error(f"All methods failed for: {item.title}")
        return False
    
    def _get_methods(self, source: BaseSource) -> list[DownloadMethod]:
        """Determine which methods to try based on source and config."""
        methods = [DownloadMethod.DIRECT]
        
        # If Tor is enabled or source requires Tor, add Tor method
        if self.config.tor_enabled or source.requires_tor:
            methods.append(DownloadMethod.TOR)
        
        # Add torrent for Anna's Archive
        if source.name == "annas-archive":
            methods.append(DownloadMethod.TORRENT)
        
        # Add mirror fallback
        methods.append(DownloadMethod.MIRROR)
        
        return methods
    
    async def _try_download(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path,
        method: DownloadMethod
    ) -> DownloadResult:
        """Try a specific download method."""
        try:
            if method == DownloadMethod.DIRECT:
                return await self._download_direct(source, item, output_path)
            
            elif method == DownloadMethod.TOR:
                return await self._download_tor(source, item, output_path)
            
            elif method == DownloadMethod.TORRENT:
                return await self._download_torrent(source, item, output_path)
            
            elif method == DownloadMethod.MIRROR:
                return await self._download_mirror(source, item, output_path)
        
        except Exception as e:
            return DownloadResult(success=False, error=str(e), method=method)
    
    async def _download_direct(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Direct download without Tor."""
        url = item.url or await source.get_download_url(item.id)
        
        if not url:
            return DownloadResult(success=False, error="No URL available")
        
        return await self._download_file(url, output_path, DownloadMethod.DIRECT)
    
    async def _download_tor(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Download via Tor proxy."""
        from ..tor.proxy import get_tor_client
        
        tor_client = get_tor_client(self.config.tor_port)
        client = tor_client.get_client()
        
        url = item.url or await source.get_download_url(item.id)
        
        if not url:
            return DownloadResult(success=False, error="No URL available")
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=self.config.chunk_size):
                    f.write(chunk)
            
            return DownloadResult(success=True, path=output_path, method=DownloadMethod.TOR)
        
        except Exception as e:
            return DownloadResult(success=False, error=str(e), method=DownloadMethod.TOR)
    
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
        
        return DownloadResult(
            success=False, 
            error="BitTorrent download not yet implemented",
            method=DownloadMethod.TORRENT
        )
    
    async def _download_mirror(
        self,
        source: BaseSource,
        item: SourceResult,
        output_path: Path
    ) -> DownloadResult:
        """Try alternative mirrors."""
        # For sources that have mirrors (like Anna's Archive)
        # Try alternative base URLs
        
        if source.name == "annas-archive":
            from ..sources.annas_archive import AnnaSource
            
            # Try alternate mirrors
            mirrors = AnnaSource.MIRRORS[1:]  # Skip first (already tried)
            
            for mirror in mirrors:
                try:
                    # Temporarily change base URL
                    old_url = source.base_url
                    source.base_url = mirror
                    
                    url = await source.get_download_url(item.id)
                    if url:
                        result = await self._download_file(url, output_path, DownloadMethod.MIRROR)
                        source.base_url = old_url
                        
                        if result.success:
                            return result
                    
                    source.base_url = old_url
                except Exception:
                    continue
        
        return DownloadResult(success=False, error="No mirrors available")
    
    async def _download_file(
        self,
        url: str,
        output_path: Path,
        method: DownloadMethod
    ) -> DownloadResult:
        """Download a file from URL."""
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
                async for chunk in response.aiter_bytes(chunk_size=self.config.chunk_size):
                    f.write(chunk)
                    pbar.update(len(chunk))
            
            return DownloadResult(
                success=True,
                path=output_path,
                method=method
            )
        
        except httpx.HTTPStatusError as e:
            return DownloadResult(
                success=False,
                error=f"HTTP {e.response.status_code}",
                method=method
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
                method=method
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None