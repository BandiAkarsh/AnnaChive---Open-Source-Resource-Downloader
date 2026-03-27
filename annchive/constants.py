"""Shared constants for annchive.

Following Linus Torvalds' principle: use named constants instead of magic numbers.
Clear names make code readable and maintainable.
"""

# ============================================================================
# CLI Display Constants
# ============================================================================

# Default limits for list/search commands
DEFAULT_LIST_LIMIT = 20
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_STATS_LIMIT = 50

# Title truncation lengths for display
TITLE_TRUNCATE_LENGTH = 50
TITLE_DISPLAY_LENGTH = 60

# ============================================================================
# Database Constants
# ============================================================================

# Query limits
DB_DEFAULT_LIMIT = 50
DB_LIST_LIMIT = 100

# Key derivation (PBKDF2)
PBKDF2_ITERATIONS = 100000
KEY_LENGTH_BYTES = 32
SALT_LENGTH_BYTES = 32

# Field index positions in database row (for _row_to_item)
# These map to: id, source, md5, title, author, format, size_bytes, path, doi, url, added_date, tags, project, notes
DB_FIELD_INDEX_TITLE = 3
DB_FIELD_INDEX_AUTHOR = 4
DB_FIELD_INDEX_DOI = 8
DB_FIELD_INDEX_NOTES = 13

# ============================================================================
# Network & HTTP Constants
# ============================================================================

# HTTP timeouts (seconds)
DEFAULT_TIMEOUT = 60
TOR_TIMEOUT = 10

# Chunk size for file downloads (bytes)
DOWNLOAD_CHUNK_SIZE = 8192

# Rate limiting
GITHUB_RATE_LIMIT_UNAUTH = 10
GITHUB_RATE_LIMIT_AUTH = 30

# arXiv-specific
ARXIV_API_URL = "https://export.arxiv.org/api"

# Git operations
GIT_CLONE_TIMEOUT = 300  # seconds (5 minutes)

# ============================================================================
# Tor Constants
# ============================================================================

DEFAULT_TOR_PORT = 9050
DEFAULT_TOR_CONTROL_PORT = 9051

# Tor connection wait timeout
TOR_WAIT_TIMEOUT = 30
TOR_CONNECT_TIMEOUT = 2

# ============================================================================
# Torrent & Download Constants
# ============================================================================

# Anna's Archive torrent API
TORRENTS_API = "https://annas-archive.org/dyn/torrents.json"

TORRENT_API_TIMEOUT = 30
TORRENT_DOWNLOAD_TIMEOUT = 60
TORRENT_DOWNLOAD_TIMEOUT_5MIN = 300

# aria2c settings
ARIA2_CONNECTIONS = 5
ARIA2_SPLITS = 10
ARIA2_SEED_TIME = 0

# ============================================================================
# Validation Constants
# ============================================================================

# MD5 hash validation
MD5_LENGTH = 32

# URL validation
MIN_URL_LENGTH = 10

# ============================================================================
# File Processing Constants
# ============================================================================

# Safe filename characters
SAFE_FILENAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")