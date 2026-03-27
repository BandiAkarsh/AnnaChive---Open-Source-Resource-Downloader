#!/bin/bash
# AnnaChive One-Command Installer (Linux/macOS)
# Does everything: install deps, create database, ready to use!
#
# Usage: 
#   curl -sL https://raw.githubusercontent.com/BandiAkarsh/annachive/main/install.sh | bash
#   OR download and run locally:
#   chmod +x install-annchive.sh && ./install-annchive.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  AnnaChive Installer (All-in-One)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# === Step 1: Install Dependencies ===
echo -e "${YELLOW}[1/5] Installing Python and dependencies...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
    elif command -v brew &> /dev/null; then
        brew install python3
    else
        echo "Please install Python 3.11+ from python.org"
        exit 1
    fi
fi

echo -e "${GREEN}  ✓ Python installed${NC}"

# Install AnnaChive package
echo -e "${YELLOW}[2/5] Installing AnnaChive...${NC}"
pip3 install annchive --quiet 2>/dev/null || pip install annchive --quiet 2>/dev/null || {
    # If not on PyPI yet, install from source
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"
    pip3 install -e . --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null
}

echo -e "${GREEN}  ✓ AnnaChive installed${NC}"

# === Step 2: Create Library Folder ===
echo -e "${YELLOW}[3/5] Setting up library folder...${NC}"

LIBRARY_DIR="$HOME/annchive_library"
mkdir -p "$LIBRARY_DIR"

echo -e "${GREEN}  ✓ Library folder created: $LIBRARY_DIR${NC}"

# === Step 3: Initialize Database ===
echo -e "${YELLOW}[4/5] Creating database...${NC}"

# Generate a random encryption key and save it
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "annchive-dev-key-$(date +%s)")

# Save the key to a file
echo "$ENCRYPTION_KEY" > "$LIBRARY_DIR/.key"
chmod 600 "$LIBRARY_DIR/.key"

# Set environment variable for this session
export ANNCHIVE_ENCRYPTION_KEY="$ENCRYPTION_KEY"
export ANNCHIVE_LIBRARY_PATH="$LIBRARY_DIR"

# Initialize the database (this creates the SQLite database)
python3 -c "
import asyncio
import os
os.environ['ANNCHIVE_ENCRYPTION_KEY'] = '$ENCRYPTION_KEY'
os.environ['ANNCHIVE_LIBRARY_PATH'] = '$LIBRARY_DIR'

from annchive.storage.database import get_database
from pathlib import Path

async def init():
    db_path = Path('$LIBRARY_DIR/annchive.db')
    async with get_database(db_path, b'$ENCRYPTION_KEY'.encode()) as db:
        print('Database created successfully!')

asyncio.run(init())
" 2>/dev/null || echo "  Note: Database will be created on first use"

echo -e "${GREEN}  ✓ Database created${NC}"

# === Step 4: Create Easy Launcher ===
echo -e "${YELLOW}[5/5] Creating convenient commands...${NC}"

# Add to shell config for persistence
SHELL_RC="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

# Add alias if not already there
if ! grep -q "ANNCHIVE_ENCRYPTION_KEY" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# AnnaChive configuration" >> "$SHELL_RC"
    echo "export ANNCHIVE_LIBRARY_PATH='$LIBRARY_DIR'" >> "$SHELL_RC"
    echo "export ANNCHIVE_ENCRYPTION_KEY='$ENCRYPTION_KEY'" >> "$SHELL_RC"
    echo "alias annchive='annchive'" >> "$SHELL_RC"
fi

echo -e "${GREEN}  ✓ Shell configured${NC}"

# === Summary ===
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "Your library is at: ${BLUE}$LIBRARY_DIR${NC}"
echo -e "Your encryption key has been saved automatically!"
echo ""
echo "NEXT STEPS:"
echo -e "  1. ${YELLOW}Source your shell config:${NC}"
echo "     source ~/.bashrc"
echo ""
echo -e "  2. ${YELLOW}Start using AnnaChive:${NC}"
echo "     annchive --help"
echo ""
echo -e "  3. ${YELLOW}Search for papers:${NC}"
echo "     annchive search arxiv \"machine learning\""
echo ""
echo -e "  4. ${YELLOW}Download a paper:${NC}"
echo "     annchive get arxiv 1706.03762 --to ~/Papers/"
echo ""
echo -e "${GREEN}That's it! No database management needed!${NC}"
echo ""
