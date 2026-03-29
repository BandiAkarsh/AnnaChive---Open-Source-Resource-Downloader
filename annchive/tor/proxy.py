"""Tor proxy client for HTTP requests."""
from typing import Optional

import httpx
import threading

from ..config import get_config


class TorClient:
    """HTTP client that routes through Tor SOCKS5 proxy.
    
    Used by sources that require Tor (e.g., Sci-Hub, onion mirrors).
    """
    
    def __init__(self, tor_port: int = 9050):
        self.tor_port = tor_port
        self._client: Optional[httpx.AsyncClient] = None
    
    def get_client(self) -> httpx.AsyncClient:
        """Get or create Tor-routed HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                proxies={
                    "all://": f"socks5://127.0.0.1:{self.tor_port}",
                },
                timeout=get_config().timeout,
                follow_redirects=True,
            )
        return self._client
    
    async def ip(self) -> str:
        """Get current IP address through Tor."""
        try:
            client = self.get_client()
            response = await client.get("https://api.ipify.org")
            return response.text.strip()
        except Exception:
            return "unknown"
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
_tor_client: Optional[TorClient] = None
_tor_client_lock = threading.Lock()


def get_tor_client(tor_port: int = 9050) -> TorClient:
    """Get global Tor client instance (singleton pattern)."""
    global _tor_client
    if _tor_client is None:
        with _tor_client_lock:
            if _tor_client is None:
                _tor_client = TorClient(tor_port)
    return _tor_client


def reset_tor_client():
    """Reset global Tor client (for testing)."""
    global _tor_client
    if _tor_client:
        import asyncio
        asyncio.create_task(_tor_client.close())
    _tor_client = None
