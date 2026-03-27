#!/bin/bash
# AnnaChive Release Builder - Cross-Platform
# Supports: Linux, macOS, Windows (via WSL or Git Bash)
# Usage: ./build-release.sh [version]

set -e

VERSION="${1:-0.1.0}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/release-$VERSION"
PLATFORM="$(uname -s)"
ARCH="$(uname -m)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "=============================================="
echo "  AnnaChive Release Builder v$VERSION"
echo "  Platform: $PLATFORM ($ARCH)"
echo "=============================================="
echo ""

# Detect Windows
is_windows() {
    case "$PLATFORM" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
}

# Create build directory
log_info "Creating build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$BUILD_DIR/python"
mkdir -p "$BUILD_DIR/rust"
mkdir -p "$BUILD_DIR/scripts"

# === Check Dependencies ===
log_info "Checking dependencies..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log_error "Python not found! Please install Python 3.11+"
    exit 1
fi
log_success "Python found: $($PYTHON_CMD --version)"

# Check pip
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    log_error "pip not found!"
    exit 1
fi
log_success "pip found"

# Check Rust (optional)
RUST_AVAILABLE=false
if command -v cargo &> /dev/null; then
    RUST_AVAILABLE=true
    log_success "Rust found: $(cargo --version)"
else
    log_warn "Rust not found - skipping binary build"
fi

# === Build Python Package ===
log_info "Building Python package..."

cd "$PROJECT_DIR"

# Upgrade pip and install build tools
$PIP_CMD install --upgrade pip setuptools wheel build --quiet 2>/dev/null || true

# Create Python source distribution
log_info "Creating source distribution..."
$PYTHON_CMD -m build --sdist --outdir "$BUILD_DIR/python" 2>/dev/null || true

# Create wheel (if possible)
log_info "Creating wheel..."
$PIP_CMD wheel . -w "$BUILD_DIR/python" --no-deps 2>/dev/null || true

# Count Python packages built
PY_COUNT=$(ls "$BUILD_DIR/python"/*.tar.gz "$BUILD_DIR/python"/*.whl 2>/dev/null | wc -l)
if [ "$PY_COUNT" -gt 0 ]; then
    log_success "Built $PY_COUNT Python package(s)"
else
    log_warn "No Python packages built (may need dependencies)"
fi

# === Build Rust Binary ===
if [ "$RUST_AVAILABLE" = true ]; then
    log_info "Building Rust torrent-downloader..."
    
    RUST_DIR="$PROJECT_DIR/cmd/torrent-download"
    if [ -d "$RUST_DIR" ]; then
        cd "$RUST_DIR"
        
        # Build for current platform
        log_info "Compiling release binary..."
        cargo build --release 2>/dev/null || true
        
        # Copy binary
        if [ -f "target/release/annchive-torrent" ]; then
            cp "target/release/annchive-torrent" "$BUILD_DIR/rust/"
            
            # Create platform-specific names
            if is_windows; then
                cp "target/release/annchive-torrent" "$BUILD_DIR/rust/annchive-torrent.exe"
            fi
            
            log_success "Rust binary built successfully"
        else
            log_warn "Rust binary not found in expected location"
        fi
        
        cd "$PROJECT_DIR"
    else
        log_warn "Rust directory not found"
    fi
else
    log_warn "Skipping Rust build (Rust not installed)"
fi

# === Create Platform-Specific Install Scripts ===
log_info "Creating installation scripts..."

# Linux/macOS installer
cat > "$BUILD_DIR/scripts/install.sh" << 'LINUX_EOF'
#!/bin/bash
# AnnaChive Installer for Linux/macOS
# Usage: ./install.sh

set -e

ANNCHIVE_VERSION="PLACEHOLDER_VERSION"
INSTALL_DIR="${HOME}/.local/annchive"
BIN_DIR="${HOME}/.local/bin"

echo "=============================================="
echo "  AnnaChive Installer"
echo "  Version: $ANNCHIVE_VERSION"
echo "=============================================="
echo ""

# Detect OS
OS="$(uname -s)"
echo "Detected OS: $OS"

# Create directories
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Install Python package
echo "Installing Python package..."
if [ -f "../python/"*.whl ]; then
    pip install ../python/*.whl --user --force-reinstall || {
        echo "Trying alternative method..."
        pip install ../python/*.tar.gz --user --force-reinstall
    }
elif [ -f "../python/"*.tar.gz ]; then
    pip install ../python/*.tar.gz --user --force-reinstall
fi

# Install Rust binary
echo "Installing torrent downloader..."
if [ -f "../rust/annchive-torrent" ]; then
    cp ../rust/annchive-torrent "$BIN_DIR/"
    chmod +x "$BIN_DIR/annchive-torrent"
elif [ -f "../rust/annchive-torrent.exe" ]; then
    cp ../rust/annchive-torrent.exe "$BIN_DIR/"
    chmod +x "$BIN_DIR/annchive-torrent.exe"
fi

# Add to PATH
SHELL_RC="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

if ! grep -q "annchive" "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
fi

# Create config directory
mkdir -p "${HOME}/.config/annchive"

echo ""
echo "=============================================="
echo "  Installation Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Set encryption key:"
echo "     export ANNCHIVE_ENCRYPTION_KEY='your-password'"
echo ""
echo "  2. Initialize AnnaChive:"
echo "     annchive init"
echo ""
echo "  3. Get help:"
echo "     annchive --help"
echo ""
echo "For more info, see: WORKFLOW.md"
echo ""
LINUX_EOF

# Windows installer (PowerShell)
cat > "$BUILD_DIR/scripts/install.ps1" << 'WINDOWS_EOF'
# AnnaChive Installer for Windows
# Usage: Run in PowerShell as Administrator

$ANNCHIVE_VERSION = "PLACEHOLDER_VERSION"
$INSTALL_DIR = "$env:LOCALAPPDATA\AnnaChive"
$BIN_DIR = "$env:LOCALAPPDATA\Programs\AnnaChive"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  AnnaChive Installer (Windows)" -ForegroundColor Cyan
Write-Host "  Version: $ANNCHIVE_VERSION" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Create directories
Write-Host "Creating installation directory..."
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null

# Install Python package
Write-Host "Installing Python package..."
if (Test-Path "../python/*.whl") {
    pip install ..\python\*.whl --user --force-reinstall
} elseif (Test-Path "../python/*.tar.gz") {
    pip install ..\python\*.tar.gz --user --force-reinstall
}

# Install Rust binary
Write-Host "Installing torrent downloader..."
if (Test-Path "../rust/annchive-torrent.exe") {
    Copy-Item "../rust/annchive-torrent.exe" "$BIN_DIR\"
}

# Add to PATH (system-level)
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*AnnaChive*") {
    [Environment]::SetEnvironmentVariable(
        "Path", 
        "$currentPath;$BIN_DIR", 
        "Machine"
    )
}

# Create config directory
$configDir = "$env:APPDATA\annchive"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Set encryption key:" -ForegroundColor White
Write-Host '     $env:ANNCHIVE_ENCRYPTION_KEY="your-password"' -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Initialize AnnaChive:" -ForegroundColor White
Write-Host "     annchive init" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Get help:" -ForegroundColor White
Write-Host "     annchive --help" -ForegroundColor Gray
Write-Host ""
WINDOWS_EOF

# Make shell script executable
chmod +x "$BUILD_DIR/scripts/install.sh"

# === Create Release Notes ===
log_info "Creating release notes..."

cat > "$BUILD_DIR/RELEASE.md" << EOF
# AnnaChive v$VERSION Release

## Download Options

### Option 1: Direct Download (This Page)
Download the files from the Releases section on GitHub.

### Option 2: Build from Source
\`\`\`bash
git clone git@github-akarsh:BandiAkarsh/annachive.git
cd annachive
./build-release.sh $VERSION
cd release-$VERSION
./scripts/install.sh
\`\`\`

## What's Included

| File | Description | Platform |
|------|-------------|----------|
| \`python/*.tar.gz\` | Source distribution | All |
| \`python/*.whl\` | Wheel package | All |
| \`rust/annchive-torrent\` | BitTorrent downloader | Linux/macOS |
| \`rust/annchive-torrent.exe\` | BitTorrent downloader | Windows |
| \`scripts/install.sh\` | Linux/macOS installer | Unix |
| \`scripts/install.ps1\` | Windows installer | Windows |

## Installation

### Linux/macOS
\`\`\`bash
# Extract
tar -xzf annachive-$VERSION.tar.gz
cd annachive-$VERSION

# Install
chmod +x scripts/install.sh
./scripts/install.sh

# Set encryption key
export ANNCHIVE_ENCRYPTION_KEY='your-password'

# Initialize
annchive init
\`\`\`

### Windows (PowerShell)
\`\`\`powershell
# Extract the archive
# Run PowerShell as Administrator

# Navigate to the scripts folder
cd annachive-$VERSION\scripts

# Run installer
.\install.ps1

# Set encryption key (in System Properties -> Environment Variables)
$env:ANNCHIVE_ENCRYPTION_KEY = "your-password"

# Initialize
annchive init
\`\`\`

## Quick Usage

\`\`\`bash
# Search for resources
annchive search arxiv "transformer"
annchive search github "python utilities"
annchive search pubmed "COVID treatment"

# Download
annchive get arxiv 1706.03762 --to ./papers/

# Enable Tor for restricted sources
annchive tor enable

# View library
annchive library list
\`\`\`

## Sources Supported

| Source | Type | Auth Required | Download Method |
|--------|------|---------------|-----------------|
| Anna's Archive | Books/Papers | ❌ No | BitTorrent |
| arXiv | Papers | ❌ No | Direct |
| GitHub | Code | ❌ No | Git clone |
| Internet Archive | Books/Media | ❌ No | Direct |
| Sci-Hub | Papers | ❌ No | Tor required |
| Semantic Scholar | Papers | ❌ No | Metadata only |
| PubMed | Abstracts | ❌ No | Direct |

## System Requirements

- **Python**: 3.11 or higher
- **pip**: Latest version recommended
- **Optional**: Tor daemon (for Sci-Hub access)
- **Optional**: Rust toolchain (for BitTorrent binary)
- **Optional**: aria2c or qBittorrent (for torrent downloads)

## Changelog

### v$VERSION
- Initial release
- Python CLI with 7 source connectors
- Rust BitTorrent downloader
- Tor integration for .onion access
- Encrypted SQLite storage

## Security

- Zero logging (privacy-first)
- Encrypted local database
- Tor anonymity support
- Local-only operation (no telemetry)

## Support

- GitHub Issues: https://github.com/BandiAkarsh/annachive/issues
- Documentation: WORKFLOW.md
EOF

# === Create Archive ===
log_info "Creating release archives..."

cd "$PROJECT_DIR"

# Create tar.gz for source (excluding build artifacts)
tar -czf "annchive-$VERSION.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='release-*' \
    --exclude='target' \
    annchive/ cmd/ tests/ pyproject.toml README.md WORKFLOW.md .gitignore

# Move to build directory
mv "annchive-$VERSION.tar.gz" "$BUILD_DIR/"

# === Summary ===
echo ""
echo "=============================================="
echo "  Release Build Complete!"
echo "=============================================="
echo ""
log_success "Output: $BUILD_DIR"
echo ""
echo "Files created:"
echo "--------------"
ls -la "$BUILD_DIR"
echo ""
echo "Python packages:"
ls -la "$BUILD_DIR/python/" 2>/dev/null || echo "  (none)"
echo ""
echo "Rust binaries:"
ls -la "$BUILD_DIR/rust/" 2>/dev/null || echo "  (none)"
echo ""
echo "Install scripts:"
ls -la "$BUILD_DIR/scripts/"
echo ""
echo "=============================================="
echo "  Next Steps to Release"
echo "=============================================="
echo ""
echo "1. Create git tag:"
echo "   git tag v$VERSION"
echo ""
echo "2. Push tag to GitHub:"
echo "   git push origin v$VERSION"
echo ""
echo "3. Create GitHub Release:"
echo "   - Go to: https://github.com/BandiAkarsh/annachive/releases/new"
echo "   - Select tag: v$VERSION"
echo "   - Upload files from: $BUILD_DIR"
echo "   - Copy content from: $BUILD_DIR/RELEASE.md"
echo ""
echo "Done! 🎉"
echo ""