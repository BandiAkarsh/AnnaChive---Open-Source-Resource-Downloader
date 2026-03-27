# AnnaChive - Component Architecture Guide

This document explains every component in AnnaChive, what it does, and why we chose it over alternatives.

---

## Table of Contents

1. [Python CLI Components](#python-cli-components)
2. [Rust Components](#rust-components)  
3. [Build & Release](#build--release)
4. [Configuration Files](#configuration-files)
5. [Why We Chose These Technologies](#why-we-chose-these-technologies)

---

## Python CLI Components

### 1. `annchive/cli.py` - Command-Line Interface

**What it does:**
- This is the main entry point - what runs when you type `annchive`
- Defines all CLI commands: search, get, library, tor, config
- Uses Click framework for CLI parsing

**Why Click over alternatives:**
| Alternative | Why We Chose Click |
|-------------|-------------------|
| argparse (built-in) | Too verbose, harder to structure |
| Typer | Good but requires more setup |
| Fire | Too magic, less control |
| **Click** | Mature, clear structure, great docs, Pythonic |

**Key decisions:**
- Used async/await for non-blocking API calls
- Grouped commands by function (search, get, library, tor)

---

### 2. `annchive/config.py` - Configuration Management

**What it does:**
- Loads settings from environment variables
- Provides defaults for everything
- Creates necessary directories

**Why environment variables:**
| Alternative | Why We Chose Environment Variables |
|-------------|----------------------------------|
| JSON config file | Less secure, harder to share |
| YAML config | Extra dependency |
| Database | Overkill for config |
| **Environment variables** | Standard, secure, portable |

---

### 3. `annchive/storage/database.py` - Encrypted Database

**What it does:**
- Stores downloaded resources in SQLite
- Encrypts sensitive data (titles, authors, notes)
- Provides fast search across your library

**Why SQLite:**
| Alternative | Why We Chose SQLite |
|-------------|---------------------|
| PostgreSQL | Overkill, requires server |
| MySQL | Overkill, requires server |
| MongoDB | Overkill, different paradigm |
| **SQLite** | Built-in, single file, fast enough |

**Why Fernet encryption:**
- Industry-standard (used by Passlib, cryptography libraries)
- Simple API - encrypt/decrypt with one key
- Authenticated encryption (can't tamper without detection)

**Why not SQLCipher:**
- Requires compilation against OpenSSL
- Harder to install on some systems
- Fernet is simpler for our use case

---

### 4. `annchive/storage/downloader.py` - Download Manager

**What it does:**
- Downloads files with progress bars
- Tries multiple methods (direct → Tor → torrent → mirrors)
- Handles retries and fallbacks automatically

**Why fallback chain:**
- Some sources are blocked in certain regions
- Tor might be slow or unavailable
- User might not have torrent client
- Fallback ensures download succeeds

---

### 5. Source Connectors (`annchive/sources/`)

Each source connector follows the same pattern:

| File | Source | API Used | Why This Source |
|------|--------|----------|-----------------|
| `arxiv.py` | arXiv.org | arXiv API | Free papers, no auth |
| `github.py` | GitHub | GitHub REST API | Code repos, free tier generous |
| `internet_archive.py` | archive.org | Archive.org API | Books, media, Wayback |
| `semantic_scholar.py` | Semantic Scholar | Semantic Scholar API | AI-powered paper search |
| `pubmed.py` | PubMed | NCBI E-utilities | Medical abstracts |
| `annas_archive.py` | Anna's Archive | Public torrents + API | Books/papers via BitTorrent |
| `scihub.py` | Sci-Hub | Various mirrors | Papers, requires Tor |

**Why these sources:**
- All are free (no paid subscriptions)
- All have public APIs or free access
- Together cover: papers, books, code, media

---

### 6. `annchive/tor/` - Tor Integration

**What it does:**
- `manager.py`: Controls Tor daemon, checks status
- `proxy.py`: Routes HTTP through Tor SOCKS5 proxy

**Why SOCKS5 over HTTP proxy:**
| Alternative | Why We Chose SOCKS5 |
|-------------|---------------------|
| HTTP proxy | Doesn't hide all traffic |
| VPN | Requires paid service |
| **SOCKS5** | Standard, works with all HTTP, true anonymity |

**Why not use stem directly for everything:**
- stem is for controlling Tor daemon
- We need a client to route HTTP through Tor
- Using httpx with SOCKS5 is simpler

---

### 7. `annchive/utils/logger.py` - Security Logging

**What it does:**
- Discards all log records (no logging)
- Protects user privacy

**Why zero logging:**
- Security-first principle
- Don't want to leak: what user searched, downloaded, etc.
- No external telemetry

---

## Rust Components

### 1. `cmd/torrent-download/Cargo.toml` - Rust Package Config

**What it does:**
- Defines dependencies for the BitTorrent module

**Why Rust for torrent:**
| Language | Why |
|----------|-----|
| Python (libtorrent) | Hard to install, bindings flaky |
| Go | Good but less mature torrent libs |
| **Rust** | Memory safe, good async, better libs |

**Key dependencies:**
- `tokio` - Best async runtime for Rust
- `reqwest` - Best HTTP client for Rust
- `clap` - Best CLI parsing for Rust

---

### 2. `cmd/torrent-download/src/main.rs` - Rust CLI Entry

**What it does:**
- CLI entry point for torrent downloader
- Commands: search, download, info, list, magnet

**Why duplicate CLI (vs Python):**
- Python does the orchestration
- Rust does the heavy lifting (BitTorrent)
- Different tools for different jobs (polyglot)

---

### 3. `cmd/torrent-download/src/anna.rs` - Anna's Archive API

**What it does:**
- Fetches torrent metadata from Anna's Archive
- Searches by MD5 hash
- Lists available torrents

**Why use their API:**
- Public, no auth needed for metadata
- Returns JSON (easy to parse)
- Free and reliable

---

### 4. `cmd/torrent-download/src/download.rs` - Torrent Download Logic

**What it does:**
- Downloads using aria2c (external tool)
- Generates magnet links
- Handles Tor routing option

**Why aria2c:**
| Alternative | Why We Chose aria2c |
|-------------|-------------------|
| libtorrent (Python) | Hard to install |
| libtorrent (Rust) | Doesn't work well |
| **aria2c** | Pre-installed on many systems, reliable |

---

### 5. `cmd/torrent-download/torrent.sh` - Shell Wrapper

**What it does:**
- Simple script to call the torrent downloader
- Falls back to aria2c if Rust binary unavailable

**Why shell wrapper:**
- Easier for users who just want to download
- Works without compiling Rust

---

## Build & Release

### 1. `build-release.sh` - Release Builder

**What it does:**
- Builds Python packages (sdist + wheel)
- Builds Rust binary
- Creates platform-specific installers
- Generates release archives

**Why bash script:**
| Alternative | Why We Chose Bash |
|-------------|-------------------|
| Makefile | Too limited |
| Python | Might not have right tools |
| **Bash** | Available everywhere, powerful |

**Features:**
- Color output for feedback
- Checks dependencies first
- Creates both `.sh` and `.ps1` installers

---

### 2. Installers

#### `scripts/install.sh` (Linux/macOS)
- Bash script
- Uses pip for Python
- Copies Rust binary to ~/.local/bin

#### `scripts/install.ps1` (Windows)
- PowerShell script
- Uses pip for Python
- Uses environment variables for PATH

**Why both bash and PowerShell:**
- Linux/macOS: bash is standard
- Windows: PowerShell is standard, cmd is limited

---

## Configuration Files

### 1. `pyproject.toml`

**What it does:**
- Defines Python package metadata
- Lists dependencies
- Configures build system
- Sets up CLI entry point

**Why this format:**
| Alternative | Why We Chose pyproject.toml |
|-------------|----------------------------|
| setup.py | Old, less standard |
| setup.cfg | Deprecated |
| **pyproject.toml** | Modern standard, all-in-one |

**Key dependencies:**
| Dependency | Purpose | Why |
|------------|---------|-----|
| click | CLI framework | Best for our use case |
| httpx | HTTP client | Async, modern API |
| stem | Tor control | Official Tor Project lib |
| aiosqlite | SQLite | Async support |
| cryptography | Encryption | Industry standard |
| tqdm | Progress bars | Pretty output |
| python-dotenv | Env vars | Easy config |

---

### 2. `.gitignore`

**What it gets rid of:**
- Python: `__pycache__`, `*.pyc`, `.pyo`
- Build: `dist/`, `build/`, `*.egg-info`
- IDE: `.vscode/`, `.idea/`
- OS: `.DS_Store`, `Thumbs.db`
- Data: `annchive_library/`, `*.db`
- Rust: `target/`, `Cargo.lock`
- Builds: `release-*/`, `*.tar.gz`

**Why these specific entries:**
- Standard Python/Rust ignores
- Plus our specific data directories
- Plus build artifacts

---

### 3. `tests/test_cli.py`

**What it does:**
- Tests CLI commands using Click's test runner
- Verifies basic functionality

**Why minimal testing:**
- This is a personal tool
- Many features depend on external APIs
- Hard to mock everything
- Manual testing sufficient for now

---

## Why We Chose These Technologies

### Python vs Other Languages

| Why Python | vs Alternatives |
|------------|-----------------|
| Rich HTTP ecosystem | Go: good but fewer libs |
| Easy CLI with Click | Java: too verbose |
| Great async support | Ruby: not as modern |
| Large community | Rust: harder to learn |

### SQLite vs Database Servers

| Why SQLite | vs Alternatives |
|------------|-----------------|
| No server needed | PostgreSQL: requires setup |
| Single file | MySQL: too complex |
| Fast enough | MongoDB: overkill |
| Portable | Cloud DBs: require internet |

### Tor over VPN

| Why Tor | vs Alternatives |
|---------|-----------------|
| Free | VPN: usually paid |
| Open source | Commercial: closed source |
| Anonymous | Proxy: less anonymous |
| Works with .onion | Standard: can't access |

### Polyglot (Python + Rust)

| Why Two Languages | vs Single Language |
|-------------------|-------------------|
| Best tool for job | Python only: torrent lib flaky |
| Python: orchestration | Rust only: harder to write CLI |
| Rust: performance | Single: compromise |

---

## Summary

AnnaChive is built with:
- **Python** for CLI, API calls, database, Tor control
- **Rust** for BitTorrent downloads (performance)
- **SQLite** for local storage (simplicity)
- **Fernet** for encryption (security)
- **Tor** for anonymous access (privacy)
- **Click** for CLI (usability)

Each choice was made after considering alternatives, prioritizing:
1. Ease of installation
2. Security and privacy
3. Reliability
4. Cross-platform support
5. Community support

---

*Last updated: March 2026*
