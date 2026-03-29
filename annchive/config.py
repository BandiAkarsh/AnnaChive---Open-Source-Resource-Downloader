"""Configuration management for annchive."""

import hashlib
import os
import threading
import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import keyring
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Keyring service name
KEYRING_SERVICE = "annchive"
KEYRING_USERNAME = "master_password_hash"


def get_master_password_hash() -> Optional[str]:
    """
    Get stored password hash from keyring or environment.
    
    Priority:
    1. ANNCHIVE_ENCRYPTION_KEY environment variable (raw password)
    2. Keyring (stored password hash)
    3. None (first-time setup)
    """
    # First check environment variable
    env_key = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    if env_key:
        return env_key
    
    # Then check keyring for stored hash
    try:
        stored_hash = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if stored_hash:
            return stored_hash
    except Exception:
        pass
    
    return None


def set_master_password(password: str) -> bool:
    """
    Store password hash securely in keyring.
    
    We store a hash of the password, not the password itself.
    The encryption key is derived from the password when needed.
    
    Args:
        password: The user's master password
        
    Returns:
        True if stored successfully
    """
    # Hash the password with salt for storage
    # This is for verification, not for deriving the encryption key
    salt = os.urandom(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    
    # Combine salt + hash for storage
    stored_value = base64.b64encode(salt).decode() + ":" + base64.b64encode(password_hash).decode()
    
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, stored_value)
        return True
    except Exception as e:
        from .utils.logger import get_logger
        logger = get_logger("config")
        logger.warning(f"Could not store password in keyring: {e}")
        return False


def verify_password(password: str) -> bool:
    """
    Verify if the provided password matches stored hash.
    
    Args:
        password: Password to verify
        
    Returns:
        True if password matches
    """
    stored = get_master_password_hash()
    if not stored:
        return False
    
    # If using environment variable, just check it matches
    if os.getenv("ANNCHIVE_ENCRYPTION_KEY"):
        return password == os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    
    # Parse stored salt:hash
    try:
        parts = stored.split(":")
        if len(parts) != 2:
            return False
        
        salt = base64.b64decode(parts[0])
        stored_hash = base64.b64decode(parts[1])
        
        # Hash provided password with same salt
        provided_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        return provided_hash == stored_hash
    except Exception:
        return False


def get_encryption_key(password: str = None) -> Optional[bytes]:
    """
    Derive encryption key from user's master password.
    
    Uses PBKDF2 with a unique salt per installation.
    Returns a Fernet-compatible key (URL-safe base64-encoded).
    
    Args:
        password: User's master password (required)
        
    Returns:
        Fernet-compatible encryption key or None if no password
    """
    import base64
    
    # Check if password provided directly
    if not password:
        # Try to get from environment
        password = os.getenv("ANNCHIVE_ENCRYPTION_KEY")
    
    if not password:
        return None
    
    # Get or create salt for key derivation
    salt = _get_or_create_salt()
    
    # Derive key using PBKDF2
    # 100,000 iterations makes brute-force attacks very slow
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, 32)
    
    # Convert to URL-safe base64 for Fernet compatibility
    fernet_key = base64.urlsafe_b64encode(key)
    
    return fernet_key


def _get_or_create_salt() -> bytes:
    """
    Get the salt for PBKDF2 key derivation.
    
    Salt is stored in ANNCHIVE_SALT env var or generated once and saved.
    Each installation should have a unique salt.
    """
    # Check environment variable first
    salt_env = os.getenv("ANNCHIVE_SALT")
    if salt_env:
        try:
            return base64.b64decode(salt_env)
        except Exception:
            pass
    
    # Generate new salt
    salt = os.urandom(32)
    salt_b64 = base64.b64encode(salt).decode()
    
    # Inform user about the salt (they should save it)
    print("\n" + "="*50)
    print("IMPORTANT: Encryption salt generated!")
    print("="*50)
    print(f"\nSave this salt securely:")
    print(f"  export ANNCHIVE_SALT='{salt_b64}'")
    print("\nAdd to your ~/.bashrc to persist across sessions.")
    print("="*50 + "\n")
    
    return salt


def generate_encryption_key() -> bytes:
    """
    Generate a random encryption key (for advanced users).
    
    Use this if you want a random key instead of password-derived.
    """
    return Fernet.generate_key()


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
    
    # Source priorities
    default_sources: str = "annas-archive,arxiv,github"
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    # Custom source URLs
    searxng_url: Optional[str] = None
    annas_mcp_path: Optional[str] = None

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
            searxng_url=os.getenv("ANNCHIVE_SEARXNG_URL"),
            annas_mcp_path=os.getenv("ANNCHIVE_ANNAS_MCP_PATH"),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            "library_path": str(self.library_path),
            "db_path": str(self.db_path),
            "encryption_enabled": self.encryption_enabled,
            "tor_enabled": self.tor_enabled,
            "tor_port": self.tor_port,
            "tor_auto_fallback": self.tor_auto_fallback,
            "default_sources": self.default_sources,
            "searxng_url": self.searxng_url or "(default)",
            "annas_mcp_path": self.annas_mcp_path or "(not set)",
        }


# Global config instance
_config: Optional[Config] = None
_config_lock = threading.Lock()
_tor_checked: bool = False


def _check_tor_connectivity(port: int) -> bool:
    """Check if Tor daemon is running and accessible."""
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
                f"Ensure Tor daemon is running."
            )
        _tor_checked = True


def reset_config():
    """Reset the global config (for testing)."""
    global _config
    _config = None
