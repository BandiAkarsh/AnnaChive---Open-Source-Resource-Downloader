#!/bin/bash
# AnnaChive Torrent Downloader - Easy wrapper script
# Usage: ./torrent.sh <md5> <output_dir> [--tor]

set -e

MD5="$1"
OUTPUT_DIR="${2:-./downloads}"
TOR_FLAG="$3"

if [ -z "$MD5" ]; then
    echo "Usage: $0 <md5> <output_dir> [--tor]"
    echo "Example: $0 abc123def456 ./papers"
    exit 1
fi

# Ensure output dir exists
mkdir -p "$OUTPUT_DIR"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Try to find the Go binary or use aria2c directly
if [ -f "$SCRIPT_DIR/target/release/annchive-torrent" ]; then
    # Use Go binary
    "$SCRIPT_DIR/target/release/annchive-torrent" download \
        --md5 "$MD5" \
        --output "$OUTPUT_DIR" \
        $([ "$TOR_FLAG" = "--tor" ] && echo "--tor" || true)
elif command -v aria2c &> /dev/null; then
    # Fallback to aria2c with Anna's Archive API
    echo "Using aria2c fallback..."
    
    # Get torrent info
    TORRENTS_JSON=$(curl -s "https://annas-archive.org/dyn/torrents.json")
    
    # Search for the file (simplified - just try magnet for now)
    echo "Note: Direct aria2c requires magnet link"
    echo "Please use the Python CLI for full functionality"
else
    echo "Error: Neither Go binary nor aria2c available"
    echo "Install aria2c: sudo apt install aria2"
    exit 1
fi