# AnnaChive

Local CLI tool for downloading open-access resources with Tor anonymity.

## Philosophy

- **Download without donation** - Uses BitTorrent method (public, no API key needed)
- **Tor for restricted sources** - Access .onion sites when needed (toggleable)
- **Fallback chain** - Try accessible method first → if fails, try alternatives
- **Encrypted storage** - SQLite with optional encryption
- **Security-first** - Zero logging, local-only, no telemetry

## Features

- Search and download from multiple sources
- Tor routing for restricted .onion sites
- Encrypted local library database
- Fallback download chain (direct → Tor → torrent → mirrors)
- CLI interface with search, library, and download commands

## Supported Sources

| Source | Auth Required | Tor Required | Notes |
|--------|---------------|--------------|-------|
| Anna's Archive | ❌ No | ❌ No | Via BitTorrent (public) |
| arXiv | ❌ No | ❌ No | Free PDF downloads |
| GitHub | ❌ No | ❌ No | Public repo cloning |
| Internet Archive | ❌ No | ❌ No | Books, media, Wayback |
| Sci-Hub | ❌ No | ✅ Yes | Via .onion (Tor required) |

## Quick Start

```bash
# Install
cd /home/akarsh/annaarchvieprojects
pip install -e .

# Initialize
annchive init

# Set encryption key (REQUIRED)
export ANNCHIVE_ENCRYPTION_KEY='your-master-key'

# Search
annchive search annas-archive "machine learning"
annchive search arxiv "neural networks"
annchive search github "python utilities"

# Enable Tor for restricted sources
annchive tor enable

# Download
annchive get annas-archive <md5> --to ./papers/
annchive get arxiv 1234.5678 --to ./papers/

# Library
annchive library list
annchive library search "python"
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required for encrypted database
ANNCHIVE_ENCRYPTION_KEY='your-master-password'

# Optional: Tor settings
ANNCHIVE_TOR_ENABLED=true
ANNCHIVE_TOR_PORT=9050

# Optional: GitHub token (for higher rate limits)
GITHUB_TOKEN=ghp_xxx
```

## Commands

```
annchive --help
annchive init                    # Initialize library
annchive config show             # Show configuration
annchive config set <key> <val> # Update config

# Search
annchive search annas-archive <query>
annchive search arxiv <query>
annchive search github <query>

# Download
annchive get annas-archive <md5> --to <dir>
annchive get arxiv <id> --to <dir>

# Library
annchive library list
annchive library search <query>
annchive library stats

# Tor
annchive tor status
annchive tor enable
annchive tor disable
annchive tor new-identity
```

## Security

- **No logging**: All logs are discarded to protect privacy
- **Local-only**: No external telemetry or analytics
- **Encrypted DB**: Optional SQLCipher encryption
- **Tor anonymity**: Toggleable routing through Tor network
- **Session isolation**: Each source has isolated credentials

## License

MIT