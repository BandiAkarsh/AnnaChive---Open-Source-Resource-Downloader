"""Tor proxy client for HTTP requests."""
# We're bringing in tools from another file
from typing import Optional

# We need help from outside - bringing in tools
import httpx

# We're bringing in tools from another file
from ..config import get_config


# Think of this like a blueprint (class) for making things
class TorClient:
    """HTTP client that routes through Tor SOCKS5 proxy.
    
    Used by sources that require Tor (e.g., Sci-Hub, onion mirrors).
    """
    
    # Here's a recipe (function) - it does a specific job
    def __init__(self, tor_port: int = 9050):
        self.tor_port = tor_port
        self._client: Optional[httpx.AsyncClient] = None
    
    # Here's a recipe (function) - it does a specific job
    def get_client(self) -> httpx.AsyncClient:
        """Get or create Tor-routed HTTP client."""
        # Checking if something is true - like asking a yes/no question
        if self._client is None:
            self._client = httpx.AsyncClient(
                # Remember this: we're calling 'proxies' something
                proxies={
                    "all://": f"socks5://127.0.0.1:{self.tor_port}",
                },
                # Remember this: we're calling 'timeout' something
                timeout=get_config().timeout,
                # Remember this: we're calling 'follow_redirects' something
                follow_redirects=True,
            )
        # We're giving back the result - like handing back what we made
        return self._client
    
    # Here's a recipe (function) - it does a specific job
    async def close(self):
        """Close the client."""
        # Checking if something is true - like asking a yes/no question
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
_tor_client: Optional[TorClient] = None


# Here's a recipe (function) - it does a specific job
def get_tor_client(tor_port: int = 9050) -> TorClient:
    """Get global Tor client instance."""
    global _tor_client
    # Checking if something is true - like asking a yes/no question
    if _tor_client is None:
        # Remember this: we're calling '_tor_client' something
        _tor_client = TorClient(tor_port)
    # We're giving back the result - like handing back what we made
    return _tor_client


# Here's a recipe (function) - it does a specific job
def reset_tor_client():
    """Reset global Tor client (for testing)."""
    global _tor_client
    # Checking if something is true - like asking a yes/no question
    if _tor_client:
        # We need help from outside - bringing in tools
        import asyncio
        asyncio.create_task(_tor_client.close())
    # Remember this: we're calling '_tor_client' something
    _tor_client = None