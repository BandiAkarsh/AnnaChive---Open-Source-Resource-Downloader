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
# Remember this: we're calling '__version__' something
__version__ = "0.1.0"

# We're bringing in tools from another file
from .config import get_config, Config
# We're bringing in tools from another file
from .storage.database import LibraryItem, EncryptedDatabase
# We're bringing in tools from another file
from .sources import (
    BaseSource,
    SourceResult,
    AnnaSource,
    ArxivSource,
    GitHubSource,
    InternetArchiveSource,
    SciHubSource,
)

# Remember this: we're calling '__all__' something
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