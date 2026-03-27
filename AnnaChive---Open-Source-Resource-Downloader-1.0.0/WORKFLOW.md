# AnnaChive - User Guide

## Quick Start (5 Minutes)

### 1. Installation

```bash
# Clone the repository
git clone git@github-akarsh:BandiAkarsh/annachive.git
cd annachive

# Install dependencies
pip install -e .

# Or with conda
conda env create -f environment.yml
conda activate annchive
```

### 2. Initial Setup

```bash
# Initialize the library
annchive init

# Set encryption key (REQUIRED for secure storage)
export ANNCHIVE_ENCRYPTION_KEY='your-secure-master-password'
# Save this key safely - you'll need it for every session

# Optional: Add to your shell config for persistence
echo "export ANNCHIVE_ENCRYPTION_KEY='your-password'" >> ~/.bashrc
```

### 3. Your First Search

```bash
# Search across all sources
annchive search arxiv "transformer architecture"

# Search a specific source
annchive search github "python utilities"
annchive search semantic-scholar "machine learning"
annchive search pubmed "COVID-19 treatment"
```

### 4. Download Resources

```bash
# Download from arXiv (free, no auth needed)
annchive get arxiv 1706.03762 --to ./papers/

# Download from GitHub
annchive get github "torvalds/linux" --to ./code/

# Enable Tor for restricted sources
annchive tor enable

# Download from Sci-Hub (requires Tor)
annchive get scihub "10.1038/nature12373" --to ./papers/
```

---

## Complete Workflow

### Understanding the Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AnnaChive CLI                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Command                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Search    │───▶│  Download   │───▶│   Library   │      │
│  │   Engine    │    │   Manager   │    │   (SQLite)  │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│       │                   │                                   │
│       ▼                   ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Source Connectors                       │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Anna's Archive  │  arXiv  │ GitHub │  PubMed  │   │    │
│  │  (via Torrent)  │ (free)  │ (free) │ (free)  │   │    │
│  │  Internet Archive│ Sci-Hub│ Semantic│        │   │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Tor Network (Optional)                  │    │
│  │    For accessing .onion sites & bypass restrictions  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Step-by-Step Workflow

#### Step 1: Search for Resources

```bash
# Search everywhere
annchive search "artificial intelligence"

# Filter by source
annchive search arxiv "deep learning"
annchive search semantic-scholar "neural networks"  
annchive search pubmed "cancer immunotherapy"
annchive search github "python framework"
annchive search internet-archive "history books"
```

#### Step 2: Review Results

The search returns:
- Title
- Author(s)
- Format (PDF, EPUB, etc.)
- Size
- Download URL or metadata

#### Step 3: Download

```bash
# Download to current directory
annchive get arxiv <paper-id> 

# Download to specific folder
annchive get arxiv <paper-id> --to ./my-papers/

# Download with custom filename
annchive get github "owner/repo" --to ./code/ --filename my-project
```

#### Step 4: Manage Your Library

```bash
# View all downloaded items
annchive library list

# Search your library
annchive library search "transformer"

# View statistics
annchive library stats
```

---

## Source-Specific Guides

### Anna's Archive (Books, Papers)
```bash
# Search
annchive search annas-archive "python programming"

# Download via BitTorrent (no donation needed!)
annchive get annas-archive <md5> --to ./books/

# Note: Uses BitTorrent - make sure you have aria2c or qBittorrent installed
```

### arXiv (Research Papers)
```bash
# arXiv ID format: YYYY.NNNNN (e.g., 1706.03762)
annchive get arxiv 1706.03762 --to ./papers/

# Search by topic
annchive search arxiv "attention is all you need"
```

### GitHub (Code)
```bash
# Clone a repository
annchive get github "owner/repo-name" --to ./projects/

# Download specific file
annchive get github "owner/repo/path/to/file.py" --to ./
```

### Internet Archive (Books, Media)
```bash
# Search
annchive search internet-archive "python tutorial"

# Download
annchive get internet-archive <identifier> --format pdf --to ./books/
```

### Semantic Scholar (Academic Papers)
```bash
# Search - returns metadata only (no direct PDF)
annchive search semantic-scholar "transformer"

# Get links to publisher sites for full text
```

### PubMed (Biomedical)
```bash
# Search biomedical literature
annchive search pubmed "mRNA vaccines"

# Download abstracts
annchive get pubmed <pmid> --to ./research/
```

### Sci-Hub (Research Papers) - Requires Tor
```bash
# Enable Tor first
annchive tor enable

# Download by DOI
annchive get scihub "10.1038/nature12373" --to ./papers/

# Check Tor status
annchive tor status
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project directory:

```bash
# Required for encrypted database
ANNCHIVE_ENCRYPTION_KEY='your-master-password'

# Optional: Tor settings
ANNCHIVE_TOR_ENABLED=true
ANNCHIVE_TOR_PORT=9050

# Optional: GitHub token (for higher rate limits)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Optional: NCBI API key (for PubMed rate limits)
NCBI_API_KEY=your-ncbi-key

# Optional: Anna's Archive donation key (for enhanced access)
ANNAS_SECRET_KEY=your-key
```

### Config Commands

```bash
# View current config
annchive config show

# Update settings
annchive config set library-path /path/to/library
annchive config set tor-enabled true
```

---

## Tor Integration

### Why Tor?
Some sources (Sci-Hub, LibGen mirrors) are blocked in certain regions. Tor routes your traffic through the Tor network to bypass these restrictions.

### Setup

```bash
# Install Tor
# Ubuntu/Debian:
sudo apt install tor

# macOS:
brew install tor

# Fedora:
sudo dnf install tor
```

### Usage

```bash
# Check Tor status
annchive tor status

# Enable Tor routing
annchive tor enable

# Disable Tor (use direct connection)
annchive tor disable

# Get new identity (new IP)
annchive tor new-identity

# Auto-fallback: If direct fails, automatically try Tor
# (Enabled by default in config)
```

---

## Security Features

| Feature | Description |
|---------|-------------|
| **Zero Logging** | No logs are written to protect privacy |
| **Encrypted DB** | SQLite database with Fernet encryption |
| **Local-Only** | No telemetry or external analytics |
| **Tor Anonymity** | Optional Tor routing for restricted sources |
| **Session Isolation** | Each source has isolated credentials |

---

## Troubleshooting

### "command not found: annchive"
```bash
# Ensure you're in the right directory
cd /path/to/annachive

# Or use full path
python -m annchive --help
```

### "Encryption key not set"
```bash
# Set the environment variable
export ANNCHIVE_ENCRYPTION_KEY='your-password'

# Verify it's set
echo $ANNCHIVE_ENCRYPTION_KEY
```

### "Tor connection failed"
```bash
# Make sure Tor is installed
which tor

# Start Tor manually
tor &

# Or check Tor service
sudo systemctl status tor
```

### "Download failed"
```bash
# Enable debug mode for more info
annchive --debug search arxiv "test"

# Check if the source is accessible
curl -I https://arxiv.org
curl -I https://api.github.com
```

---

## Advanced Usage

### Batch Downloads
```bash
# Download multiple papers
for id in 1706.03762 1810.04805 1907.11615; do
    annchive get arxiv $id --to ./papers/
done
```

### Scripting
```bash
#!/bin/bash
# Download papers from a list
while read line; do
    annchive get arxiv "$line" --to ./papers/
done < papers.txt
```

### Using with Other Tools
```bash
# Convert PDF to text
pdftotext paper.pdf

# Extract from EPUB
ebook-extract book.epub

# Search in downloaded files
grep -r "keyword" ./papers/
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `annchive init` | Initialize library |
| `annchive search <source> <query>` | Search for resources |
| `annchive get <source> <id>` | Download a resource |
| `annchive library list` | List downloaded items |
| `annchive library search <query>` | Search library |
| `annchive library stats` | Show statistics |
| `annchive tor status` | Check Tor status |
| `annchive tor enable` | Enable Tor |
| `annchive tor disable` | Disable Tor |
| `annchive config show` | Show configuration |
| `annchive --help` | Show help |

---

## Support

- GitHub Issues: https://github.com/BandiAkarsh/annachive/issues
- Documentation: https://github.com/BandiAkarsh/annachive#readme

---

## Philosophy

AnnaChive follows these principles:

1. **Download without donation** - Uses BitTorrent (no API key needed)
2. **Tor for restricted access** - Bypass regional blocks via onion sites
3. **Fallback-first** - Try accessible methods, then alternatives
4. **Encrypted storage** - Your library, your data, secured
5. **Security-first** - Zero logging, local-only, no telemetry
6. **Polyglot architecture** - Best tool for each job (Python + Rust)
