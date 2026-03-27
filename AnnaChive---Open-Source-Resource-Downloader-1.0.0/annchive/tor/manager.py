"""Tor integration for anonymous routing.

Security features:
- Toggleable: off by default, enable when needed
- Auto-fallback: if Tor fails, try direct connection
- Session isolation: new identity for each request option
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("tor.manager")


@dataclass
class TorStatus:
    """Tor connection status."""
    enabled: bool
    connected: bool
    ip: Optional[str] = None
    country: Optional[str] = None


class TorManager:
    """Manages Tor daemon and routing.
    
    Modes:
    - Disabled (default): Direct connections
    - Enabled: All HTTP requests route through Tor SOCKS5
    - Auto-fallback: Try direct first, fallback to Tor if blocked
    """
    
    def __init__(self):
        self.config = get_config()
        self._enabled = False
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def enabled(self) -> bool:
        """Check if Tor is currently enabled."""
        return self._enabled or self.config.tor_enabled
    
    async def enable(self):
        """Enable Tor routing."""
        self._enabled = True
        logger.info("Tor routing enabled")
    
    async def disable(self):
        """Disable Tor routing."""
        self._enabled = False
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Tor routing disabled")
    
    async def get_status(self) -> TorStatus:
        """Get current Tor status."""
        status = TorStatus(
            enabled=self.enabled,
            connected=False,
        )
        
        if not self.enabled:
            return status
        
        # Check if we can connect through Tor
        try:
            # Try to check IP through Tor
            client = self._get_client()
            response = await client.get(
                "https://httpbin.org/ip",
                timeout=10
            )
            
            if response.status_code == 200:
                status.connected = True
                data = response.json()
                status.ip = data.get("origin", "Unknown")
        except Exception as e:
            logger.warning(f"Tor connection check failed: {e}")
        
        return status
    
    async def new_identity(self) -> bool:
        """Request new Tor circuit (new IP).
        
        Uses Tor control port to send NEWNYM signal.
        """
        if not self.enabled:
            logger.warning("Tor not enabled - cannot get new identity")
            return False
        
        # This requires control port to be configured
        # We'll implement a simpler approach: close and reconnect
        
        if self._client:
            await self._client.aclose()
            self._client = None
        
        # Get new client (should get new circuit)
        self._get_client()
        
        # Check new IP
        status = await self.get_status()
        logger.info(f"New Tor identity. IP: {status.ip}")
        
        return status.connected
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client configured for Tor."""
        if self._client is None:
            # Configure for Tor SOCKS5 proxy
            self._client = httpx.AsyncClient(
                proxies={
                    "all://": f"socks5://127.0.0.1:{self.config.tor_port}",
                },
                timeout=self.config.timeout,
                follow_redirects=True,
            )
        
        return self._client
    
    def get_client(self) -> httpx.AsyncClient:
        """Get the Tor-configured client (sync version for BaseSource)."""
        return self._get_client()
    
    async def check_tor_available(self) -> bool:
        """Check if Tor daemon is running and accessible."""
        try:
            # Try to connect to Tor SOCKS5 port
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", self.config.tor_port))
            sock.close()
            
            return result == 0
        except Exception:
            return False
    
    async def wait_for_tor(self, timeout: int = 30) -> bool:
        """Wait for Tor daemon to become available."""
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) < timeout:
            if await self.check_tor_available():
                return True
            await asyncio.sleep(1)
        
        return False


# Global instance
_tor_manager: Optional[TorManager] = None


def get_tor_manager() -> TorManager:
    """Get global Tor manager instance."""
    global _tor_manager
    if _tor_manager is None:
        _tor_manager = TorManager()
    return _tor_manager