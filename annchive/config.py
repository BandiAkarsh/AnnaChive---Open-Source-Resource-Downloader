"""Configuration management for annchive."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()


@dataclass
class Config:
    """Main configuration for annchive."""

    # Library settings
    library_path: Path = field(
        default_factory=lambda: Path.home() / "annchive_library"
    )
    
    # Database settings
    db_path: Path = field(
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

    def __post_init__(self):
        """Ensure paths exist."""
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            library_path=Path(os.getenv("ANNCHIVE_LIBRARY_PATH", 
                str(Path.home() / "annchive_library"))),
            db_path=Path(os.getenv("ANNCHIVE_DB_PATH", 
                str(Path.home() / "annchive_library" / "annchive.db"))),
            encryption_enabled=os.getenv("ANNCHIVE_ENCRYPTION", "true").lower() == "true",
            tor_enabled=os.getenv("ANNCHIVE_TOR_ENABLED", "false").lower() == "true",
            tor_port=int(os.getenv("ANNCHIVE_TOR_PORT", "9050")),
            tor_control_port=int(os.getenv("ANNCHIVE_TOR_CONTROL_PORT", "9051")),
            tor_auto_fallback=os.getenv("ANNCHIVE_TOR_AUTO_FALLBACK", "true").lower() == "true",
            max_retries=int(os.getenv("ANNCHIVE_MAX_RETRIES", "3")),
            timeout=int(os.getenv("ANNCHIVE_TIMEOUT", "60")),
            default_sources=os.getenv("ANNCHIVE_DEFAULT_SOURCES", 
                "annas-archive,arxiv,github"),
            cache_enabled=os.getenv("ANNCHIVE_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("ANNCHIVE_CACHE_TTL", "3600")),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary (for display)."""
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


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config():
    """Reset the global config (for testing)."""
    global _config
    _config = None