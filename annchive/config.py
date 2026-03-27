"""Configuration management for annchive."""
# We need help from outside - bringing in tools
import os
# We're bringing in tools from another file
from dataclasses import dataclass, field
# We're bringing in tools from another file
from pathlib import Path
# We're bringing in tools from another file
from typing import Optional

# We're bringing in tools from another file
import threading

# We're bringing in tools from another file
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()


@dataclass
# Think of this like a blueprint (class) for making things
class Config:
    """Main configuration for annchive."""

    # Library settings
    library_path: Path = field(
        # Remember this: we're calling 'default_factory' something
        default_factory=lambda: Path.home() / "annchive_library"
    )
    
    # Database settings
    db_path: Path = field(
        # Remember this: we're calling 'default_factory' something
        default_factory=lambda: Path.home() / "annchive_library" / "annchive.db"
    )
    encryption_enabled: bool = True
    
    # Tor settings
    tor_enabled: bool = False
    tor_port: int = 9050
    tor_control_port: int = 9051
    tor_auto_fallback: bool = True
    
    # Download settings
    max_retries: int = 3
    timeout: int = 60
    chunk_size: int = 8192
    
    # Source priorities (comma-separated list)
    default_sources: str = "annas-archive,arxiv,github"
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds

    # Here's a recipe (function) - it does a specific job
    def __post_init__(self):
        """Ensure paths exist."""
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    # Here's a recipe (function) - it does a specific job
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # We're giving back the result - like handing back what we made
        return cls(
            # Remember this: we're calling 'library_path' something
            library_path=Path(os.getenv("ANNCHIVE_LIBRARY_PATH", 
                str(Path.home() / "annchive_library"))),
            # Remember this: we're calling 'db_path' something
            db_path=Path(os.getenv("ANNCHIVE_DB_PATH", 
                str(Path.home() / "annchive_library" / "annchive.db"))),
            # Remember this: we're calling 'encryption_enabled' something
            encryption_enabled=os.getenv("ANNCHIVE_ENCRYPTION", "true").lower() == "true",
            # Remember this: we're calling 'tor_enabled' something
            tor_enabled=os.getenv("ANNCHIVE_TOR_ENABLED", "false").lower() == "true",
            # Remember this: we're calling 'tor_port' something
            tor_port=int(os.getenv("ANNCHIVE_TOR_PORT", "9050")),
            # Remember this: we're calling 'tor_control_port' something
            tor_control_port=int(os.getenv("ANNCHIVE_TOR_CONTROL_PORT", "9051")),
            # Remember this: we're calling 'tor_auto_fallback' something
            tor_auto_fallback=os.getenv("ANNCHIVE_TOR_AUTO_FALLBACK", "true").lower() == "true",
            # Remember this: we're calling 'max_retries' something
            max_retries=int(os.getenv("ANNCHIVE_MAX_RETRIES", "3")),
            # Remember this: we're calling 'timeout' something
            timeout=int(os.getenv("ANNCHIVE_TIMEOUT", "60")),
            # Remember this: we're calling 'default_sources' something
            default_sources=os.getenv("ANNCHIVE_DEFAULT_SOURCES", 
                "annas-archive,arxiv,github"),
            # Remember this: we're calling 'cache_enabled' something
            cache_enabled=os.getenv("ANNCHIVE_CACHE_ENABLED", "true").lower() == "true",
            # Remember this: we're calling 'cache_ttl' something
            cache_ttl=int(os.getenv("ANNCHIVE_CACHE_TTL", "3600")),
        )
    
    # Here's a recipe (function) - it does a specific job
    def to_dict(self) -> dict:
        """Convert to dictionary (for display)."""
        # We're giving back the result - like handing back what we made
        return {
            "library_path": str(self.library_path),
            "db_path": str(self.db_path),
            "encryption_enabled": self.encryption_enabled,
            "tor_enabled": self.tor_enabled,
            "tor_port": self.tor_port,
            "tor_auto_fallback": self.tor_auto_fallback,
            "default_sources": self.default_sources,
        }


# Global config instance
_config: Optional[Config] = None
_config_lock = threading.Lock()
_tor_checked: bool = False


def _check_tor_connectivity(port: int) -> bool:
    """Check if Tor daemon is running and accessible on the given port.
    
    Args:
        port: The Tor SOCKS port to check
        
    Returns:
        True if Tor is accessible, False otherwise
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    global _tor_checked
    
    # Double-checked locking pattern for thread safety
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = Config.from_env()
                _check_tor_connectivity_safe(_config)
    
    return _config


def _check_tor_connectivity_safe(config):
    """Check Tor connectivity if Tor is enabled."""
    global _tor_checked
    if config.tor_enabled and not _tor_checked:
        if not _check_tor_connectivity(config.tor_port):
            from .utils.logger import get_logger
            logger = get_logger("config")
            logger.warning(
                f"Tor is enabled (port {config.tor_port}) but cannot connect. "
                f"Ensure Tor daemon is running. Download functionality via Tor will fail."
            )
        _tor_checked = True


# Here's a recipe (function) - it does a specific job
def reset_config():
    """Reset the global config (for testing).
    
    Note: This clears the config instance. Any active connections
    (database, HTTP clients) should be closed before resetting.
    For proper cleanup, close any active resources first.
    """
    global _config
    # Note: Caller should ensure proper cleanup of any active resources
    # (database connections, HTTP clients, etc.) before calling reset
    _config = None