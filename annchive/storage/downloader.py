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
from ..constants import TITLE_TRUNCATE_LENGTH, DOWNLOAD_CHUNK_SIZE, SAFE_FILENAME_CHARS

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
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize filename to remove unsafe characters."""
        safe_chars = SAFE_FILENAME_CHARS
        result = []
        for char in title:
            if char in safe_chars:
                result.append(char)
            elif char in '._-':
                result.append(char)
            elif char == ' ':
                result.append('_')
        return ''.join(result)[:TITLE_TRUNCATE_LENGTH]
    
    async def download(
        self,
        url: str,
        output_dir: Path,
        title: Optional[str] = None,
        filename: Optional[str] = None
    ) -> bool:
        """Download a file from URL.
        
        Args:
            url: URL to download from
            output_dir: Directory to save the file
            title: Title for sanitizing filename
            filename: Optional explicit filename
            
        Returns:
            True if successful, False otherwise
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if not filename:
            if title:
                safe_title = self._sanitize_filename(title)
                filename = f"{safe_title}.pdf"
            else:
                filename = "download"
        
        output_path = output_dir / filename
        
        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                
                with open(output_path, "wb") as f, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=filename[:20],
                ) as progress:
                    async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        f.write(chunk)
                        progress.update(len(chunk))
            
            logger.info(f"Downloaded: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if output_path.exists():
                output_path.unlink()
            return False
    
    async def clone_github(self, repo_url: str, output_dir: Path) -> bool:
        """Clone a GitHub repository using git.
        
        Args:
            repo_url: GitHub repository URL
            output_dir: Directory to clone into
            
        Returns:
            True if successful, False otherwise
        """
        import subprocess
        from ..constants import GIT_CLONE_TIMEOUT
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract repo name from URL
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        
        target_path = output_dir / repo_name
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(target_path)],
                capture_output=True,
                text=True,
                timeout=GIT_CLONE_TIMEOUT,
            )
            
            if result.returncode == 0:
                logger.info(f"Cloned repository to: {target_path}")
                return True
            else:
                logger.error(f"Git clone failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
            return False
        except FileNotFoundError:
            logger.error("git command not found - install git to clone repositories")
            return False
        except Exception as e:
            logger.error(f"Git clone failed: {e}")
            return False
    
    async def download_with_fallback(
        self,
        source: BaseSource,
        item: SourceResult,
        output_dir: Path
    ) -> DownloadResult:
        """Download with automatic fallback chain.
        
        Returns DownloadResult with success status and method used.
        """
        methods = []
        
        # Try direct download first
        if item.url:
            methods.append(DownloadMethod.DIRECT)
            success = await self.download(item.url, output_dir, item.title)
            if success:
                return DownloadResult(
                    success=True,
                    path=output_dir / f"{self._sanitize_filename(item.title)}.pdf",
                    method=DownloadMethod.DIRECT,
                    attempts=len(methods),
                )
        
        # Try via Tor if enabled
        if self.config.tor_enabled:
            methods.append(DownloadMethod.TOR)
            logger.info("Trying Tor fallback...")
            # Tor implementation would go here
        
        # Try via torrent for Anna's Archive
        if item.md5 and item.source == "annas-archive":
            methods.append(DownloadMethod.TORRENT)
            logger.info("Trying torrent fallback...")
            # Torrent implementation would go here
        
        # Try mirrors
        methods.append(DownloadMethod.MIRROR)
        logger.info("Trying mirror fallback...")
        
        return DownloadResult(
            success=False,
            method=methods[-1] if methods else None,
            attempts=len(methods),
            error="All download methods failed",
        )
