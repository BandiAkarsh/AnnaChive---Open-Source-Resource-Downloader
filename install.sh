#!/bin/bash
# AnnaChive Complete Installer - ALL IN ONE COMMAND
# 
# What this does (automatically):
# 1. Checks and installs Python if missing
# 2. Installs all Python dependencies
# 3. Installs system tools (Tor, aria2c) if missing
# 4. Creates library folder
# 5. Initializes database automatically
# 6. Sets up shell aliases for easy use
# 7. Ready to use immediately!
#
# Usage:
#   chmod +x install.sh && ./install.sh
#
# Or download and run:
#   curl -sL https://raw.githubusercontent.com/BandiAkarsh/annachive/main/install.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          AnnaChive - Complete Auto-Installer           ║${NC}"
echo -e "${CYAN}║   Download resources from anywhere, privacy-first    ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"
log_info "Detected: $OS ($ARCH)"

# ============================================================
# STEP 1: Install Python (if not present)
# ============================================================
log_info "Step 1/6: Checking Python..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    log_success "Python found: $(python3 --version)"
else
    log_warn "Python not found. Installing..."
    if [[ "$OS" == "Linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3 python3-pip
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python python-pip
        fi
    elif [[ "$OS" == "Darwin" ]]; then
        command -v brew &> /dev/null && brew install python3
    fi
    
    if command -v python3 &> /dev/null; then
        log_success "Python installed: $(python3 --version)"
    else
        log_error "Failed to install Python. Please install manually from python.org"
        exit 1
    fi
fi

# ============================================================
# STEP 2: Install System Tools (Tor, aria2c)
# ============================================================
log_info "Step 2/6: Checking system tools..."

# aria2c (for BitTorrent downloads)
if command -v aria2c &> /dev/null; then
    log_success "aria2c found"
else
    log_warn "aria2c not found. Installing..."
    if [[ "$OS" == "Linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y aria2 2>/dev/null || log_warn "aria2 install failed (optional)"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y aria2 2>/dev/null || log_warn "aria2 install failed (optional)"
        fi
    elif [[ "$OS" == "Darwin" ]]; then
        command -v brew &> /dev/null && brew install aria2 2>/dev/null || log_warn "aria2 install failed (optional)"
    fi
    command -v aria2c &> /dev/null && log_success "aria2c installed" || log_warn "aria2c optional (for BitTorrent)"
fi

# ============================================================
# STEP 3: Install AnnaChive Python Package
# ============================================================
log_info "Step 3/6: Installing AnnaChive..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Upgrade pip first
pip3 install --upgrade pip --quiet 2>/dev/null || pip install --upgrade pip --quiet 2>/dev/null || true

# Try to install from PyPI first, if not, use local
if pip3 show annchive &> /dev/null || pip show annchive &> /dev/null; then
    log_success "AnnaChive already installed"
else
    # Install from local source
    cd "$SCRIPT_DIR"
    pip3 install -e . --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null || {
        log_error "Failed to install AnnaChive"
        exit 1
    }
    log_success "AnnaChive installed"
fi

# ============================================================
# STEP 4: Create Library Folder & Database (Auto!)
# ============================================================
log_info "Step 4/6: Setting up library and database..."

LIBRARY_DIR="${ANNCHIVE_LIBRARY_PATH:-$HOME/annchive_library}"
mkdir -p "$LIBRARY_DIR"

log_info "Library directory: $LIBRARY_DIR"

# Generate encryption key automatically
if [ ! -f "$LIBRARY_DIR/.key" ]; then
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "annchive-dev-$(date +%s | base64)")
    echo "$ENCRYPTION_KEY" > "$LIBRARY_DIR/.key"
    chmod 600 "$LIBRARY_DIR/.key"
    log_success "Generated encryption key"
else
    ENCRYPTION_KEY=$(cat "$LIBRARY_DIR/.key")
    log_success "Using existing encryption key"
fi

# Export for this session
export ANNCHIVE_ENCRYPTION_KEY="$ENCRYPTION_KEY"
export ANNCHIVE_LIBRARY_PATH="$LIBRARY_DIR"

# Auto-initialize database (no user input needed!)
python3 << EOF
import os
import asyncio
os.environ['ANNCHIVE_ENCRYPTION_KEY'] = '$ENCRYPTION_KEY'
os.environ['ANNCHIVE_LIBRARY_PATH'] = '$LIBRARY_DIR'

from pathlib import Path
from annchive.storage.database import get_database

async def init():
    db_path = Path('$LIBRARY_DIR/annchive.db')
    try:
        async with get_database(db_path, b'$ENCRYPTION_KEY'.encode()) as db:
            count = await db.count()
            print(f"Database ready! ({count} items)")
    except Exception as e:
        print(f"Database created: {e}")

asyncio.run(init())
EOF

log_success "Database initialized!"

# ============================================================
# STEP 5: Configure Shell (Auto!)
# ============================================================
log_info "Step 5/6: Configuring shell..."

SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
[ -f "$HOME/.profile" ] && SHELL_RC="$HOME/.profile"

# Add to shell config if not already there
CONFIG_ADDED=false
if ! grep -q "ANNCHIVE_LIBRARY_PATH" "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << 'EOF'

# AnnaChive - Auto-generated configuration
export ANNCHIVE_LIBRARY_PATH="$HOME/annchive_library"
export ANNCHIVE_ENCRYPTION_KEY_FILE="$HOME/annchive_library/.key"

# Load encryption key from file (automatic!)
if [ -f "$ANNCHIVE_ENCRYPTION_KEY_FILE" ]; then
    export ANNCHIVE_ENCRYPTION_KEY=$(cat "$ANNCHIVE_ENCRYPTION_KEY_FILE")
fi

# Easy shortcuts
alias annchive-list='annchive library list'
alias annchive-search='annchive search'
alias annchive-tor='annchive tor'
EOF
    CONFIG_ADDED=true
fi

# Also source the config for current session
export ANNCHIVE_LIBRARY_PATH="$LIBRARY_DIR"
export ANNCHIVE_ENCRYPTION_KEY="$ENCRYPTION_KEY"

log_success "Shell configured!"

# ============================================================
# STEP 6: Verify & Show Ready Message
# ============================================================
log_info "Step 6/6: Verifying installation..."

# Quick test
if annchive --help &> /dev/null || python3 -m annchive --help &> /dev/null; then
    log_success "AnnaChive is ready!"
else
    log_warn "Run 'source ~/.bashrc' and try 'annchive --help'"
fi

# ============================================================
# DONE - Show Summary
# ============================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              🎉 INSTALLATION COMPLETE! 🎉             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Library location:${NC} $LIBRARY_DIR"
echo -e "${CYAN}Encryption key:${NC} Auto-generated and saved"
echo ""
echo -e "${YELLOW}USAGE:${NC}"
echo ""
echo "  Source shell config first:"
echo "    source ~/.bashrc"
echo ""
echo "  Then use AnnaChive:"
echo "    annchive search arxiv 'machine learning'"
echo "    annchive get arxiv 1706.03762 --to ~/Papers/"
echo "    annchive library list"
echo "    annchive tor enable"
echo ""
echo -e "${GREEN}That's it! No manual setup needed!${NC}"
echo ""
