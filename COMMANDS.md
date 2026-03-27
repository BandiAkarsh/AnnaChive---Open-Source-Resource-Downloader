# AnnaChive Command Reference

Complete documentation for all AnnaChive commands with examples.

---

## Getting Help

### Show All Commands
```bash
annchive --help
# or
annchive -h
```

### Get Help for Specific Command
```bash
annchive search --help
annchive get --help
annchive library --help
annchive tor --help
```

---

## Command Categories

| Category | Commands |
|----------|----------|
| **Setup** | `init`, `config` |
| **Search** | `search` |
| **Download** | `get` |
| **Library** | `library` |
| **Privacy** | `tor` |

---

## Setup Commands

### `annchive init`

Initialize AnnaChive - creates library folder and database.

```bash
# Default setup
annchive init

# Custom library location
annchive init --library-path /path/to/my/library

# Without encryption
annchive init --no-encrypt
```

**What it does:**
- Creates library folder
- Creates encrypted SQLite database
- Sets up configuration

---

### `annchive config`

Manage configuration settings.

```bash
# Show all settings
annchive config show

# Set a value
annchive config set tor-enabled true
annchive config set library-path /new/path
```

---

## Search Commands

### `annchive search`

Search for resources across different sources.

```bash
# Search all sources
annchive search "machine learning"

# Search specific source
annchive search arxiv "neural networks"
annchive search github "python utilities"
annchive search semantic-scholar "transformer"
annchive search pubmed "COVID treatment"
annchive search internet-archive "python tutorial"
annchive search annas-archive "python programming"

# Limit results
annchive search arxiv "AI" --limit 5
```

**Available sources:**
| Source | What It Searches |
|--------|-----------------|
| `arxiv` | Research papers |
| `github` | Code repositories |
| `semantic-scholar` | Academic papers (metadata) |
| `pubmed` | Medical/bio papers |
| `internet-archive` | Books, media, Wayback |
| `annas-archive` | Books, papers, Z-Lib |
| `scihub` | Papers (requires Tor) |

---

## Download Commands

### `annchive get`

Download resources from various sources.

```bash
# Download from arXiv
annchive get arxiv 1706.03762 --to ./papers/

# Download from GitHub
annchive get github "owner/repo-name" --to ./code/

# Download from PubMed (abstract)
annchive get pubmed 12345678 --to ./research/

# Download from Internet Archive
annchive get internet-archive <identifier> --to ./books/

# Download from Anna's Archive (requires BitTorrent)
annchive get annas-archive <md5> --to ./books/

# Enable Tor for restricted sources first
annchive tor enable
annchive get scihub "10.1038/nature12373" --to ./papers/
```

**Common arXiv IDs:**
- `1706.03762` - Attention Is All You Need (Transformer)
- `1810.04805` - BERT paper
- `1907.11615` - RoBERTa

---

## Library Commands

### `annchive library`

Manage your local collection.

```bash
# List all downloaded items
annchive library list

# List with limit
annchive library list --limit 20

# Filter by source
annchive library list --source arxiv
annchive library list --source github

# Filter by project
annchive library list --project my-research

# Search within your library
annchive library search "python"
annchive library search "transformer"

# Show statistics
annchive library stats
```

**Add items to library manually:**
```bash
annchive library add \
  --source arxiv \
  --title "Attention Is All You Need" \
  --author "Vaswani et al." \
  --format pdf \
  --path ~/papers/attention.pdf \
  --project my-research \
  --tags "machine-learning,nlp"
```

---

## Tor Commands

### `annchive tor`

Manage Tor connection for anonymous access.

```bash
# Check Tor status
annchive tor status

# Enable Tor routing
annchive tor enable

# Disable Tor (use direct connection)
annchive tor disable

# Get new identity (new IP)
annchive tor new-identity
```

**Why use Tor?**
- Access blocked content (Sci-Hub, some mirrors)
- Bypass regional restrictions
- Anonymous browsing

---

## Environment Variables

AnnaChive uses these environment variables:

| Variable | Purpose | Required? |
|---------|---------|-----------|
| `ANNCHIVE_ENCRYPTION_KEY` | Encryption password | Yes (for encrypted DB) |
| `ANNCHIVE_LIBRARY_PATH` | Where to store files | No (default: ~/annchive_library) |
| `ANNCHIVE_TOR_ENABLED` | Enable Tor by default | No |
| `GITHUB_TOKEN` | GitHub API token (for higher rate limits) | No |
| `NCBI_API_KEY` | PubMed API key | No |

**Set once in your shell config:**
```bash
# In ~/.bashrc or ~/.zshrc
export ANNCHIVE_ENCRYPTION_KEY='your-password'
export ANNCHIVE_LIBRARY_PATH='/path/to/library'
```

---

## Quick Reference

| Task | Command |
|------|---------|
| First time setup | `annchive init` |
| Search papers | `annchive search arxiv "topic"` |
| Download paper | `annchive get arxiv <id> --to ~/Papers/` |
| View library | `annchive library list` |
| Enable Tor | `annchive tor enable` |
| Check config | `annchive config show` |
| Get help | `annchive --help` |

---

## Troubleshooting

### "command not found"
```bash
# Make sure Python package is installed
pip show annchive

# Or run directly
python -m annchive --help
```

### "Encryption key not set"
```bash
# Set the key
export ANNCHIVE_ENCRYPTION_KEY='your-password'
```

### "Download failed"
```bash
# Enable debug mode
annchive --debug search arxiv "test"

# Or enable Tor for restricted sources
annchive tor enable
```

### "Database locked"
```bash
# Close any other AnnaChive sessions
# Try again
```

---

## Examples

### Download a Research Paper
```bash
# Find the paper
annchive search arxiv "attention is all you need"
# Output shows: 1706.03762

# Download it
annchive get arxiv 1706.03762 --to ~/Papers/Transformer/

# View your library
annchive library list
```

### Clone a GitHub Repository
```bash
# Search for repository
annchive search github "python machine learning"

# Clone it
annchive get github "popular/python-repo" --to ~/Projects/
```

### Download from Multiple Sources
```bash
# Enable Tor first (for restricted sources)
annchive tor enable

# Download from different sources
annchive get arxiv 1706.03762 --to ./papers/
annchive get github "tensorflow/tensorflow" --to ./code/
annchive get scihub "10.1038/nature12373" --to ./papers/
annchive get pubmed 32812345 --to ./research/
```

---

## Keyboard Shortcuts

There are no keyboard shortcuts - this is a CLI tool! Just type commands.

---

## Next Steps

1. **Set your encryption key:** `export ANNCHIVE_ENCRYPTION_KEY='your-password'`
2. **Initialize:** `annchive init`
3. **Search:** `annchive search arxiv "your topic"`
4. **Download:** `annchive get <source> <id> --to <directory>`
5. **View library:** `annchive library list`

That's it! Happy downloading! 📚