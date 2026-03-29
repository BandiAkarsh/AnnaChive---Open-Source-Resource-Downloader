"""BitTorrent download support for Anna's Archive.

This module handles downloading from Anna's Archive torrents without requiring
a donation. Uses public torrent metadata to get file info.

Anna's Archive provides:
- Torrent files: https://annas-archive.org/torrents
- Metadata JSON: https://annas-archive.org/dyn/torrents.json
- Byte offsets for selective download

Strategy:
1. Fetch torrent info from Anna's Archive metadata
2. Use libtorrent to download specific files from torrent
3. Alternative: use aria2c with torrent file
"""
import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import get_config
from ..utils.logger import get_logger
from ..constants import (
    TORRENTS_API, TORRENT_DOWNLOAD_TIMEOUT, TORRENT_DOWNLOAD_TIMEOUT_5MIN,
    ARIA2_CONNECTIONS, ARIA2_SPLITS, ARIA2_SEED_TIME
)

logger = get_logger("storage.torrent")


@dataclass
class TorrentInfo:
    """Information about a torrent file."""
    info_hash: str
    name: str
    size: int
    files: list[dict]
    trackers: list[str]
    torrent_url: Optional[str] = None


class TorrentManager:
    """Manages BitTorrent downloads for Anna's Archive.
    
    Supports multiple backends:
    1. libtorrent (Python bindings) - most control
    2. aria2c (CLI tool) - easier to use, no Python dependencies
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.config = get_config()
        self.output_dir = output_dir or self.config.library_path
    
    async def get_torrent_info(self, md5: str) -> Optional[TorrentInfo]:
        """Get torrent information for a file by MD5 hash."""
        url = f"{TORRENTS_API}"
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=TORRENT_DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                # Find matching entry by MD5
                for entry in data.get("torrents", []):
                    if entry.get("md5") == md5:
                        return TorrentInfo(
                            info_hash=entry.get("infoHash", ""),
                            name=entry.get("fileName", ""),
                            size=entry.get("contentLength", 0),
                            files=entry.get("files", []),
                            trackers=entry.get("trackers", []),
                            torrent_url=entry.get("torrentUrl"),
                        )
        except Exception as e:
            logger.error(f"Failed to get torrent info: {e}")
        
        return None
    
    async def download_with_aria2(self, torrent_info: TorrentInfo, output_path: Path) -> bool:
        """Download using aria2c CLI tool."""
        if not torrent_info.torrent_url:
            logger.error("No torrent URL available")
            return False
        
        cmd = [
            "aria2c",
            "-d", str(output_path.parent),
            "-o", output_path.name,
            "-s", str(ARIA2_SPLITS),
            "-x", str(ARIA2_CONNECTIONS),
            "--seed-time", str(ARIA2_SEED_TIME),
            torrent_info.torrent_url,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TORRENT_DOWNLOAD_TIMEOUT_5MIN,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error("aria2c download timed out")
            return False
        except Exception as e:
            logger.error(f"aria2c failed: {e}")
            return False
    
    def generate_magnet_link(self, torrent_info: TorrentInfo) -> str:
        """Generate a magnet link for manual download."""
        trackers = "&tr=".join(torrent_info.trackers) if torrent_info.trackers else ""
        return f"magnet:?xt=urn:btih:{torrent_info.info_hash}&dn={torrent_info.name}{trackers}"
    
    async def download(
        self,
        md5: str,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """Download a file by MD5 hash using torrent.
        
        Args:
            md5: MD5 hash of the file to download
            output_dir: Directory to save the file
            
        Returns:
            Path to downloaded file, or None if failed
        """
        output_dir = output_dir or self.output_dir
        
        # Get torrent info
        torrent_info = await self.get_torrent_info(md5)
        if not torrent_info:
            logger.error(f"No torrent found for MD5: {md5}")
            return None
        
        output_path = output_dir / torrent_info.name
        
        # Try aria2c first
        if await self.download_with_aria2(torrent_info, output_path):
            return output_path
        
        # Fallback: return magnet link for manual download
        magnet = self.generate_magnet_link(torrent_info)
        logger.info(f"aria2c failed. Use this magnet link: {magnet}")
        
        return None
    
    async def list_available_torrents(self, query: Optional[str] = None, limit: int = 50) -> list[dict]:
        """List available torrents from Anna's Archive.
        
        Args:
            query: Optional search query
            limit: Maximum results to return
            
        Returns:
            List of torrent metadata dictionaries
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(TORRENTS_API, timeout=TORRENT_DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                torrents = data.get("torrents", [])
                
                if query:
                    query_lower = query.lower()
                    torrents = [
                        t for t in torrents
                        if query_lower in t.get("fileName", "").lower()
                    ]
                
                return torrents[:limit]
        except Exception as e:
            logger.error(f"Failed to list torrents: {e}")
            return []
    
    async def get_file_info(self, md5: str) -> Optional[dict]:
        """Get detailed file information from Anna's Archive metadata.
        
        Args:
            md5: MD5 hash of the file
            
        Returns:
            File metadata dictionary or None
        """
        url = "https://annas-archive.org/dyn/metadata"
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"md5": md5}, timeout=TORRENT_DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return None
