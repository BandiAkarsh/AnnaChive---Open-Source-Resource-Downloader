# Man Page Installation Guide

## Quick Install (Linux/macOS)

```bash
# Copy to man page directory
sudo cp annchive.1 /usr/local/share/man/man1/

# Compress (optional, saves space)
sudo gzip /usr/local/share/man/man1/annchive.1

# Now view with:
man annchive
```

## User-Level Install (No sudo)

```bash
# Create local man directory
mkdir -p ~/.local/share/man/man1

# Copy man page
cp annchive.1 ~/.local/share/man/man1/

# Add to MANPATH (add to ~/.bashrc or ~/.zshrc)
export MANPATH="$HOME/.local/share/man:$MANPATH"

# View with:
man annchive
```

## Verify Installation

```bash
# Check man can find it
man -w annchive

# Or view directly
man annchive
```

## Uninstallation

```bash
# Remove from system man directory
sudo rm /usr/local/share/man/man1/annchive.1.gz

# Or user-level
rm ~/.local/share/man/man1/annchive.1
```