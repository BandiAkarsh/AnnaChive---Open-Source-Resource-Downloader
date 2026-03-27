"""AnnaChive - Local CLI for open-access resources with Tor anonymity.

Core Philosophy:
- Download open-source articles and resources for local/offline access
- Access restricted sources via Tor (onion sites)
- No donation required - uses public endpoints and BitTorrent
- Security-first: zero logging, encrypted storage, local-only

Sources supported:
- Anna's Archive (via BitTorrent - no donation needed)
- arXiv (free, no auth)
- GitHub (free, no auth)
- Internet Archive (free, no auth)
- Sci-Hub (via Tor, .onion access)
"""
__version__ = "0.1.0"

from .config import get_config, Config
from .storage.database import LibraryItem, EncryptedDatabase
from .sources import (
    BaseSource,
    SourceResult,
    AnnaSource,
    ArxivSource,
    GitHubSource,
    InternetArchiveSource,
    SciHubSource,
)

__all__ = [
    "__version__",
    "get_config",
    "Config",
    "LibraryItem",
    "EncryptedDatabase",
    "BaseSource",
    "SourceResult",
    "AnnaSource",
    "ArxivSource",
    "GitHubSource", 
    "InternetArchiveSource",
    "SciHubSource",
]