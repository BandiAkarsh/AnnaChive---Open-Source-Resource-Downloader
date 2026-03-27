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
    2. aria2c - external tool, easier to install
    3.qbittorrent-nox - daemon mode
    """
    
    # Anna's Archive torrent metadata endpoint
    TORRENTS_API = "https://annas-archive.org/dyn/torrents.json"
    
    # Known torrents with file metadata
    METADATA_TORRENTS = [
        "aa_derived_mirror_metadata",
        "zlib3",
        "libgen_lc", 
        "libgen_scimag",
        "scihub",
    ]
    
    def __init__(self):
        self.config = get_config()
        self._client = None
    
    async def search_metadata(self, md5: str) -> Optional[TorrentInfo]:
        """Search Anna's Archive torrent metadata for a file.
        
        This searches the public metadata to find which torrent contains
        a file with the given MD5 hash.
        """
        import httpx
        
        # Fetch the torrents JSON (public, no auth needed)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self.TORRENTS_API)
                response.raise_for_status()
                data = response.json()
                
                # Search through available torrents
                for torrent in data.get("torrents", []):
                    files = torrent.get("files", [])
                    for f in files:
                        if f.get("md5") == md5:
                            return TorrentInfo(
                                info_hash=torrent.get("info_hash", ""),
                                name=torrent.get("name", ""),
                                size=torrent.get("size", 0),
                                files=torrent.get("files", []),
                                trackers=torrent.get("trackers", []),
                            )
                        
        except Exception as e:
            logger.error(f"Failed to search torrent metadata: {e}")
        
        return None
    
    async def get_torrent_file(self, info_hash: str) -> Optional[bytes]:
        """Download the .torrent file for a given info hash.
        
        Anna's Archive provides torrent files via their CDN.
        """
        import httpx
        
        # Construct torrent download URL
        # Anna's Archive uses: https://annas-archive.org/torrent/{info_hash}
        url = f"https://annas-archive.org/torrent/{info_hash}"
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"Failed to download torrent file: {e}")
            return None
    
    async def download_with_aria2c(
        self, 
        magnet: str, 
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download using aria2c (external tool).
        
        This is a fallback if libtorrent isn't available.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if aria2c is available
        try:
            subprocess.run(
                ["aria2c", "--version"], 
                check=True, 
                capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("aria2c not found, cannot use torrent download")
            return None
        
        # Build aria2c command
        cmd = [
            "aria2c",
            magnet,
            "--dir", str(output_dir),
            "--seed-time=0",  # Stop seeding after download
            "--max-connection-per-server=5",
            "--split=10",  # Use multiple connections
        ]
        
        if filename:
            cmd.extend(["--out", filename])
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            
            # Find the downloaded file
            if filename:
                downloaded = output_dir / filename
                if downloaded.exists():
                    logger.info(f"Downloaded via aria2c: {filename}")
                    return downloaded
                    
        except subprocess.TimeoutExpired:
            logger.error("aria2c download timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"aria2c failed: {e.stderr}")
        
        return None
    
    async def download_with_qbittorrent(
        self,
        torrent_path: Path,
        output_dir: Path
    ) -> Optional[Path]:
        """Download using qBittorrent (via web API).
        
        Requires qBittorrent running with web UI enabled.
        """
        # Check for qbtcli or qbittorrent
        # This is a placeholder - would need web API config
        logger.info("qBittorrent download not implemented")
        return None
    
    def generate_magnet(self, info_hash: str, name: str) -> str:
        """Generate a magnet link from info hash and name."""
        return f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
    
    async def download(
        self,
        md5: str,
        output_dir: Path,
        filename: Optional[str] = None
    ) -> Optional[Path]:
        """Download a file from Anna's Archive via BitTorrent.
        
        This is the main entry point for torrent downloads.
        
        Args:
            md5: MD5 hash of the file to download
            output_dir: Directory to save to
            filename: Optional filename
        
        Returns:
            Path to downloaded file, or None if failed
        """
        # Step 1: Find which torrent contains this file
        logger.info(f"Searching for MD5: {md5} in torrent metadata...")
        
        torrent_info = await self.search_metadata(md5)
        
        if not torrent_info:
            logger.error(f"Could not find file with MD5: {md5}")
            return None
        
        logger.info(f"Found in torrent: {torrent_info.name}")
        
        # Step 2: Download the torrent file
        torrent_data = await self.get_torrent_file(torrent_info.info_hash)
        
        if not torrent_data:
            # Fallback: try magnet link
            magnet = self.generate_magnet(
                torrent_info.info_hash, 
                torrent_info.name
            )
            logger.info(f"Using magnet: {magnet[:50]}...")
            
            return await self.download_with_aria2c(magnet, output_dir, filename)
        
        # Step 3: Save torrent file and use it
        torrent_file = output_dir / f"{torrent_info.info_hash}.torrent"
        torrent_file.write_bytes(torrent_data)
        
        logger.info(f"Saved torrent file: {torrent_file}")
        
        # Use aria2c with torrent file
        # This would be enhanced with libtorrent in production
        return await self.download_with_aria2c(
            str(torrent_file),
            output_dir,
            filename
        )


# Convenience function
async def download_from_annas(md5: str, output_dir: Path) -> Optional[Path]:
    """Download a file from Anna's Archive using BitTorrent."""
    tm = TorrentManager()
    return await tm.download(md5, output_dir)