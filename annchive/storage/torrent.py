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
# We need help from outside - bringing in tools
import asyncio
# We need help from outside - bringing in tools
import json
# We need help from outside - bringing in tools
import subprocess
# We're bringing in tools from another file
from dataclasses import dataclass
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
from ..config import get_config
# We're bringing in tools from another file
from ..utils.logger import get_logger
# Shared constants - avoid magic numbers
from ..constants import (
    TORRENTS_API, TORRENT_DOWNLOAD_TIMEOUT, TORRENT_DOWNLOAD_TIMEOUT_5MIN,
    ARIA2_CONNECTIONS, ARIA2_SPLITS, ARIA2_SEED_TIME
)

# Remember this: we're calling 'logger' something
logger = get_logger("storage.torrent")


@dataclass
# Think of this like a blueprint (class) for making things
class TorrentInfo:
    """Information about a torrent file."""
    info_hash: str
    name: str
    size: int
    files: list[dict]
    trackers: list[str]
    torrent_url: Optional[str] = None


# Think of this like a blueprint (class) for making things
class TorrentManager:
    """Manages BitTorrent downloads for Anna's Archive.
    
    Supports multiple backends:
    1. libtorrent (Python bindings) - most control
    2. aria2c - external tool, easier to install
    3.qbittorrent-nox - daemon mode
    """
    
    # Known torrents with file metadata
    # Remember this: we're calling 'METADATA_TORRENTS' something
    METADATA_TORRENTS = [
        "aa_derived_mirror_metadata",
        "zlib3",
        "libgen_lc", 
        "libgen_scimag",
        "scihub",
    ]
    
    # Here's a recipe (function) - it does a specific job
    def __init__(self):
        self.config = get_config()
        self._client = None
    
    # Here's a recipe (function) - it does a specific job
    async def search_metadata(self, md5: str) -> Optional[TorrentInfo]:
        """Search Anna's Archive torrent metadata for a file.
        
        This searches the public metadata to find which torrent contains
        a file with the given MD5 hash.
        """
        # We need help from outside - bringing in tools
        import httpx
        
        # Fetch the torrents JSON (public, no auth needed)
        # We're trying something that might go wrong
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Remember this: we're calling 'response' something
                response = await client.get(self.TORRENTS_API)
                response.raise_for_status()
                # Remember this: we're calling 'data' something
                data = response.json()
                
                # Search through available torrents
                # We're doing something over and over, like a repeat button
                for torrent in data.get("torrents", []):
                    # Remember this: we're calling 'files' something
                    files = torrent.get("files", [])
                    # We're doing something over and over, like a repeat button
                    for f in files:
                        # Checking if something is true - like asking a yes/no question
                        if f.get("md5") == md5:
                            # We're giving back the result - like handing back what we made
                            return TorrentInfo(
                                # Remember this: we're calling 'info_hash' something
                                info_hash=torrent.get("info_hash", ""),
                                # Remember this: we're calling 'name' something
                                name=torrent.get("name", ""),
                                # Remember this: we're calling 'size' something
                                size=torrent.get("size", 0),
                                # Remember this: we're calling 'files' something
                                files=torrent.get("files", []),
                                # Remember this: we're calling 'trackers' something
                                trackers=torrent.get("trackers", []),
                            )
                        
        except Exception as e:
            logger.error(f"Failed to search torrent metadata: {e}")
        
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def get_torrent_file(self, info_hash: str) -> Optional[bytes]:
        """Download the .torrent file for a given info hash.
        
        Anna's Archive provides torrent files via their CDN.
        """
        # We need help from outside - bringing in tools
        import httpx
        
        # Construct torrent download URL
        # Anna's Archive uses: https://annas-archive.org/torrent/{info_hash}
        # Remember this: we're calling 'url' something
        url = f"https://annas-archive.org/torrent/{info_hash}"
        
        # We're trying something that might go wrong
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Remember this: we're calling 'response' something
                response = await client.get(url)
                response.raise_for_status()
                # We're giving back the result - like handing back what we made
                return response.content
        except Exception as e:
            logger.error(f"Failed to download torrent file: {e}")
            # We're giving back the result - like handing back what we made
            return None
    
    # Here's a recipe (function) - it does a specific job
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
        # We're trying something that might go wrong
        try:
            subprocess.run(
                ["aria2c", "--version"], 
                # Remember this: we're calling 'check' something
                check=True, 
                # Remember this: we're calling 'capture_output' something
                capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("aria2c not found, cannot use torrent download")
            # We're giving back the result - like handing back what we made
            return None
        
        # Build aria2c command
        # Remember this: we're calling 'cmd' something
        cmd = [
            "aria2c",
            magnet,
            "--dir", str(output_dir),
            "--seed-time=0",  # Stop seeding after download
            "--max-connection-per-server=5",
            "--split=10",  # Use multiple connections
        ]
        
        # Checking if something is true - like asking a yes/no question
        if filename:
            cmd.extend(["--out", filename])
        
        # We're trying something that might go wrong
        try:
            # Remember this: we're calling 'result' something
            result = subprocess.run(
                cmd,
                # Remember this: we're calling 'check' something
                check=True,
                # Remember this: we're calling 'capture_output' something
                capture_output=True,
                # Remember this: we're calling 'text' something
                text=True,
                # Remember this: we're calling 'timeout' something
                timeout=300  # 5 min timeout
            )
            
            # Find the downloaded file
            # Checking if something is true - like asking a yes/no question
            if filename:
                # Remember this: we're calling 'downloaded' something
                downloaded = output_dir / filename
                # Checking if something is true - like asking a yes/no question
                if downloaded.exists():
                    logger.info(f"Downloaded via aria2c: {filename}")
                    # We're giving back the result - like handing back what we made
                    return downloaded
                    
        except subprocess.TimeoutExpired:
            logger.error("aria2c download timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"aria2c failed: {e.stderr}")
        
        # We're giving back the result - like handing back what we made
        return None
    
    # Here's a recipe (function) - it does a specific job
    async def download_with_qbittorrent(
        self,
        torrent_path: Path,
        output_dir: Path
    ) -> Optional[Path]:
        """Download using qBittorrent (via web API).
        
        Requires qBittorrent running with web UI enabled at http://localhost:8080
        with default credentials (admin:admin).
        
        Args:
            torrent_path: Path to .torrent file
            output_dir: Directory to save downloaded files
            
        Returns:
            Path to downloaded file, or None if failed
        """
        return await self._download_with_qbittorrent_impl(torrent_path, output_dir)
    
    async def _download_with_qbittorrent_impl(self, torrent_path: Path, output_dir: Path) -> Optional[Path]:
        """Implementation of qBittorrent download."""
        import httpx
        import os
        
        qbt_url = os.getenv("ANNCHIVE_QBITTORRENT_URL", "http://localhost:8080")
        username = os.getenv("ANNCHIVE_QBITTORRENT_USER", "admin")
        password = os.getenv("ANNCHIVE_QBITTORRENT_PASS", "admin")
        
        try:
            async with httpx.AsyncClient(timeout=TORRENT_API_TIMEOUT) as client:
                login_resp = await client.post(
                    f"{qbt_url}/api/v2/auth/login",
                    data={"username": username, "password": password}
                )
                if login_resp.status_code != 200:
                    logger.warning("qBittorrent login failed")
                    return None
                
                with open(torrent_path, "rb") as f:
                    files = {"file": f}
                    add_resp = await client.post(
                        f"{qbt_url}/api/v2/torrents/add",
                        files=files,
                        data={"savepath": str(output_dir)}
                    )
                
                if add_resp.status_code != 200:
                    logger.warning(f"qBittorrent add failed: {add_resp.text}")
                    return None
                
                logger.info("Torrent added to qBittorrent")
                return None
        except Exception as e:
            logger.warning(f"qBittorrent download failed: {e}")
            return None
                
        except Exception as e:
            logger.warning(f"qBittorrent download failed: {e}")
            return None
    
    # Here's a recipe (function) - it does a specific job
    def generate_magnet(self, info_hash: str, name: str) -> str:
        """Generate a magnet link from info hash and name."""
        # We're giving back the result - like handing back what we made
        return f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
    
    # Here's a recipe (function) - it does a specific job
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
        torrent_info = await self._find_torrent_for_file(md5)
        if not torrent_info:
            return None
        
        return await self._download_torrent_file(torrent_info, output_dir, filename)
    
    async def _find_torrent_for_file(self, md5: str) -> Optional[TorrentInfo]:
        """Find which torrent contains the file with given MD5."""
        logger.info(f"Searching for MD5: {md5} in torrent metadata...")
        torrent_info = await self.search_metadata(md5)
        
        if not torrent_info:
            logger.error(f"Could not find file with MD5: {md5}")
            return None
        
        logger.info(f"Found in torrent: {torrent_info.name}")
        return torrent_info
    
    async def _download_torrent_file(
        self, torrent_info: TorrentInfo, output_dir: Path, filename: Optional[str]
    ) -> Optional[Path]:
        """Download using torrent file or magnet link."""
        torrent_data = await self.get_torrent_file(torrent_info.info_hash)
        
        if not torrent_data:
            return await self._download_with_magnet(torrent_info, output_dir, filename)
        
        return await self._download_with_torrent_file(torrent_info, torrent_data, output_dir, filename)
    
    async def _download_with_magnet(
        self, torrent_info: TorrentInfo, output_dir: Path, filename: Optional[str]
    ) -> Optional[Path]:
        """Fallback to magnet link download."""
        magnet = self.generate_magnet(torrent_info.info_hash, torrent_info.name)
        logger.info(f"Using magnet: {magnet[:50]}...")
        return await self.download_with_aria2c(magnet, output_dir, filename)
    
    async def _download_with_torrent_file(
        self, torrent_info: TorrentInfo, torrent_data: bytes, output_dir: Path, filename: Optional[str]
    ) -> Optional[Path]:
        """Download using torrent file."""
        torrent_file = output_dir / f"{torrent_info.info_hash}.torrent"
        torrent_file.write_bytes(torrent_data)
        logger.info(f"Saved torrent file: {torrent_file}")
        return await self.download_with_aria2c(str(torrent_file), output_dir, filename)


# Convenience function
# Here's a recipe (function) - it does a specific job
async def download_from_annas(md5: str, output_dir: Path) -> Optional[Path]:
    """Download a file from Anna's Archive using BitTorrent."""
    # Remember this: we're calling 'tm' something
    tm = TorrentManager()
    # We're giving back the result - like handing back what we made
    return await tm.download(md5, output_dir)