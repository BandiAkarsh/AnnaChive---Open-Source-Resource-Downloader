# AnnaChive

Local CLI tool for downloading open-access resources with Tor anonymity.

## What is AnnaChive?

AnnaChive is a command-line tool that helps you download free resources from the internet:
- Research papers from arXiv, Semantic Scholar, PubMed
- Books from Anna's Archive, Internet Archive  
- Code from GitHub
- Academic papers via Sci-Hub (requires Tor)

**Core Philosophy:**
- Download without donation - uses public methods (BitTorrent)
- Tor for restricted sources - access blocked content
- Encrypted storage - your library, your data
- Security-first - no logging, local-only

## Installation

### Option 1: Install from GitHub Release (Recommended for Users)

```bash
# Download the latest release from:
# https://github.com/BandiAkarsh/annachive/releases

# Extract the archive
tar -xzf annachive-0.1.0.tar.gz
cd annachive-0.1.0

# Run the installer
# For Linux/macOS:
chmod +x scripts/install.sh
./scripts/install.sh

# For Windows (PowerShell):
# .\scripts\install.ps1
```

### Option 2: Install from Source (For Developers)

```bash
# Clone the repository
git clone git@github-akarsh:BandiAkarsh/annachive.git
cd annachave

# Install the Python package
# Option A: Install in development mode (editable)
pip install -e .

# Option B: Install globally
sudo pip install .

# Option C: Install for current user
pip install --user .
```

### Option 3: Build Your Own Release

```bash
# Clone and build
git clone git@github-akarsh:BandiAkarsh/annachive.git
cd annachive

# Run the release builder
./build-release.sh 0.1.0

# Find your release in: release-0.1.0/
```

## First-Time Setup

After installation, follow these three steps:

### Step 1: Set Encryption Key (REQUIRED)
```bash
# This key encrypts your library database - YOU MUST SET THIS
export ANNCHIVE_ENCRYPTION_KEY='your-secure-password'

# Make it permanent (add to your shell config)
echo "export ANNCHIVE_ENCRYPTION_KEY='your-password'" >> ~/.bashrc
source ~/.bashrc
```

### Step 2: Initialize AnnaChive
```bash
# This creates the library folder and database
annchive init
```

### Step 3: Verify It Works
```bash
annchive --help
```

---

## What Does `annchive init` Do?

When you run `annchive init`, it:

1. **Creates a library folder** - Where your downloads will be stored
   - Default: `~/annchive_library/`
   - Or wherever you specify with `--library-path`

2. **Creates a database** - Tracks everything you download
   - File: `~/annchive_library/annchive.db`
   - This database is encrypted!

3. **Sets up the configuration** - Gets everything ready to use

**Example output:**
```
Initialized at: /home/username/annchive_library
Encryption: enabled
```

---

## How to Use After Installation

### Basic Workflow

```bash
# 1. Make sure encryption key is set (every session)
export ANNCHIVE_ENCRYPTION_KEY='your-password'

# 2. Search for something
annchive search arxiv "transformer"

# 3. Download what you need
annchive get arxiv 1706.03762 --to ./papers/

# 4. View your library
annchive library list
```

### Full Command Reference

| Command | What It Does | Example |
|---------|--------------|---------|
| `annchive init` | Create library folder + database | `annchive init` |
| `annchive search <source> <query>` | Find resources | `annchive search arxiv "AI"` |
| `annchive get <source> <id>` | Download a resource | `annchive get arxiv 1706.03762 --to ./papers/` |
| `annchive library list` | See your downloads | `annchive library list` |
| `annchive library search <query>` | Search in your library | `annchive library search "python"` |
| `annchive tor enable` | Enable Tor for restricted sources | `annchive tor enable` |
| `annchive config show` | View your settings | `annchive config show` |

### Without Setting Key First

If you don't set the encryption key, you'll get an error:
```
ERROR: Encryption key not set
```

**Fix:** Run this before any other command:
```bash
export ANNCHIVE_ENCRYPTION_KEY='your-password'
```

## Quick Start Guide

### Searching for Resources

```bash
# Search everywhere
annchive search arxiv "machine learning"

# Search specific sources
annchive search github "python utilities"
annchive search semantic-scholar "neural networks"
annchive search pubmed "COVID treatment"
```

### Downloading

```bash
# Download from arXiv (paper ID like 1706.03762)
annchive get arxiv 1706.03762 --to ./papers/

# Download from GitHub
annchive get github "owner/repo-name" --to ./code/

# Enable Tor for restricted sources
annchive tor enable

# Download via Tor (for Sci-Hub, etc.)
annchive get scihub "10.1038/nature12373" --to ./papers/
```

### Managing Your Library

```bash
# See all downloaded items
annchive library list

# Search your library
annchive library search "python"

# See statistics
annchive library stats
```

## Supported Sources

| Source | What You'll Get | Free? | Tor? |
|--------|-----------------|-------|------|
| **arXiv** | Research papers (PDF) | ✅ Yes | ❌ No |
| **GitHub** | Code repositories | ✅ Yes | ❌ No |
| **Internet Archive** | Books, media | ✅ Yes | ❌ No |
| **Semantic Scholar** | Paper metadata | ✅ Yes | ❌ No |
| **PubMed** | Medical abstracts | ✅ Yes | ❌ No |
| **Anna's Archive** | Books, papers | ✅ Yes | ❌ No |
| **Sci-Hub** | Research papers | ✅ Yes | ✅ Yes |

## Configuration

### Environment Variables

Create a `.env` file or set these in your shell:

```bash
# REQUIRED: Encryption key for your library
ANNCHIVE_ENCRYPTION_KEY='your-master-password'

# Optional: Enable Tor by default
ANNCHIVE_TOR_ENABLED=true

# Optional: Custom library location
ANNCHIVE_LIBRARY_PATH='/path/to/library'

# Optional: GitHub token (for more requests)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### Config Commands

```bash
# View current settings
annchive config show

# Change settings
annchive config set tor-enabled true
annchive config set library-path /new/path
```

## Tor Integration

Some sources (like Sci-Hub) are blocked in certain countries. AnnaChive can route through Tor to bypass these blocks.

```bash
# Check if Tor is running
annchive tor status

# Enable Tor routing
annchive tor enable

# Disable Tor (use direct connection)
annchive tor disable

# Get new identity (new IP address)
annchive tor new-identity
```

## Command Reference

| Command | What It Does |
|---------|--------------|
| `annchive init` | Set up your library |
| `annchive search <source> <query>` | Find resources |
| `annchive get <source> <id>` | Download a resource |
| `annchive library list` | See downloads |
| `annchive library search <query>` | Search library |
| `annchive tor enable` | Turn on Tor |
| `annchive config show` | View settings |

## Troubleshooting

### "annchive: command not found"
```bash
# Make sure pip installed it correctly
pip show annchive

# Or try running it directly
python -m annchive --help

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

### "Encryption key not set"
```bash
# Set the environment variable
export ANNCHIVE_ENCRYPTION_KEY='your-password'
```

### "Download failed"
```bash
# Enable debug mode for details
annchive --debug search arxiv "test"
```

## Security Features

- **Zero Logging**: No information about your downloads is ever saved
- **Encrypted Database**: Your library is encrypted
- **Local Only**: No data is sent to external servers
- **Tor Option**: Anonymous browsing when needed

## License

MIT - Free to use, modify, and distribute.

## Support

- GitHub Issues: https://github.com/BandiAkarsh/annachive/issues
- Full Guide: See WORKFLOW.md
