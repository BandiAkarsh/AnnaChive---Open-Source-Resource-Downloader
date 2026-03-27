# AnnaChive Complete Installer (Windows PowerShell)
# 
# What this does (automatically):
# 1. Checks and installs Python if missing
# 2. Installs all Python dependencies
# 3. Creates library folder
# 4. Initializes database automatically
# 5. Ready to use immediately!
#
# Usage:
#   1. Download this file
#   2. Right-click -> Run with PowerShell
#   3. Or: .\install.ps1

# Check if running as Admin (for system-wide installs)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          AnnaChive Complete Installer (Windows)        ║" -ForegroundColor Cyan
Write-Host "║   Download resources from anywhere, privacy-first     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonVersion = python --version
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Python not found. Installing..." -ForegroundColor Yellow
    
    # Download and install Python
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    try {
        Write-Host "  Downloading Python..." -ForegroundColor Gray
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -OutFile $pythonInstaller -UseBasicParsing
        
        Write-Host "  Installing Python (this may take a minute)..." -ForegroundColor Gray
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Host "  [OK] Python installed" -ForegroundColor Green
    }
    catch {
        Write-Host "  [ERROR] Failed to install Python. Please install from python.org" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Install dependencies
Write-Host "[2/5] Installing dependencies..." -ForegroundColor Yellow

# Upgrade pip
python -m pip install --upgrade pip --quiet 2>$null

# Install AnnaChive
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

python -m pip install -e . --quiet 2>$null
Write-Host "  [OK] AnnaChive installed" -ForegroundColor Green

# Step 3: Create Library
Write-Host "[3/5] Creating library folder..." -ForegroundColor Yellow

$libraryDir = "$env:USERPROFILE\annchive_library"
if (-not (Test-Path $libraryDir)) {
    New-Item -ItemType Directory -Force -Path $libraryDir | Out-Null
}
Write-Host "  Library: $libraryDir" -ForegroundColor Gray

# Step 4: Generate encryption key
Write-Host "[4/5] Setting up encryption..." -ForegroundColor Yellow

$keyFile = "$libraryDir\.key"
if (-not (Test-Path $keyFile)) {
    $encryptionKey = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    $encryptionKey | Out-File -FilePath $keyFile -Encoding UTF8
    Write-Host "  [OK] Encryption key generated" -ForegroundColor Green
} else {
    $encryptionKey = Get-Content $keyFile
    Write-Host "  [OK] Using existing key" -ForegroundColor Green
}

# Set environment variables for current session
$env:ANNCHIVE_LIBRARY_PATH = $libraryDir
$env:ANNCHIVE_ENCRYPTION_KEY = $encryptionKey

# Initialize database
python << 'PYEOF'
import os
import asyncio
os.environ['ANNCHIVE_LIBRARY_PATH'] = r'%LIBRARY_DIR%'
os.environ['ANNCHIVE_ENCRYPTION_KEY'] = r'%ENCRYPTION_KEY%'

from pathlib import Path
from annchive.storage.database import get_database

async def init():
    db_path = Path(r'%LIBRARY_DIR%') / 'annchive.db'
    async with get_database(db_path, r'%ENCRYPTION_KEY%'.encode()) as db:
        count = await db.count()
        print(f"Database ready! ({count} items)")

asyncio.run(init())
PYEOF

Write-Host "  [OK] Database initialized" -ForegroundColor Green

# Step 5: Create launcher script
Write-Host "[5/5] Creating shortcuts..." -ForegroundColor Yellow

$launcher = "$env:USERPROFILE\annchive.ps1"
@"
# AnnaChive Launcher (Auto-generated)
`$env:ANNCHIVE_LIBRARY_PATH = "$libraryDir"
`$env:ANNCHIVE_ENCRYPTION_KEY = "$encryptionKey"

# Run AnnaChive
annchive `$args
"@ | Out-File -FilePath $launcher -Encoding UTF8

Write-Host "  [OK] Shortcuts created" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "           INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Library: $libraryDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "USAGE:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Option 1: Using annachive command:" -ForegroundColor White
Write-Host "    annchive search arxiv `"machine learning`""
Write-Host "    annchive get arxiv 1706.03762 --to `"`$HOME\Papers`""
Write-Host "    annchive library list"
Write-Host ""
Write-Host "  Option 2: Using launcher:" -ForegroundColor White
Write-Host "    $launcher search arxiv `"machine learning`""
Write-Host ""
Write-Host "That's it! No manual setup needed!" -ForegroundColor Green
Write-Host ""
