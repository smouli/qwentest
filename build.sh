#!/bin/bash
# Build script for Render deployment
# This script sets up the Rust/Cargo environment to use a writable directory

set -e  # Exit on error

echo "=== Starting build script ==="
echo "HOME: $HOME"
echo "PWD: $(pwd)"

# Set CARGO_HOME to a writable directory BEFORE any cargo/maturin operations
export CARGO_HOME="$HOME/.cargo"
export RUSTUP_HOME="$HOME/.rustup"

echo "CARGO_HOME: $CARGO_HOME"
echo "RUSTUP_HOME: $RUSTUP_HOME"

# Create cargo directories structure
mkdir -p "$CARGO_HOME/registry/cache"
mkdir -p "$CARGO_HOME/registry/index"
mkdir -p "$CARGO_HOME/git"
mkdir -p "$RUSTUP_HOME"

# Ensure these directories are writable
chmod -R u+w "$CARGO_HOME" 2>/dev/null || true
chmod -R u+w "$RUSTUP_HOME" 2>/dev/null || true

echo "Created Cargo directories"

# Check if cargo is available and configure it to use our CARGO_HOME
if command -v cargo &> /dev/null; then
    echo "Cargo found: $(which cargo)"
    echo "Configuring Cargo to use CARGO_HOME=$CARGO_HOME"
    # Create a cargo config file to ensure it uses our registry location
    mkdir -p "$CARGO_HOME"
    cat > "$CARGO_HOME/config.toml" << EOF
[registry]
default = "crates-io"

[net]
git-fetch-with-cli = true
EOF
else
    echo "Cargo not found in PATH"
fi

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
# Export environment variables to ensure subprocesses inherit them
export CARGO_HOME
export RUSTUP_HOME

# Verify environment variables are set
echo "Environment check:"
echo "  CARGO_HOME=$CARGO_HOME"
echo "  RUSTUP_HOME=$RUSTUP_HOME"

# Set environment in a way that persists through all subprocess calls
# This ensures maturin and cargo subprocesses inherit these variables
export CARGO_HOME
export RUSTUP_HOME

# Also set them in the current shell's environment file if it exists
if [ -f ~/.bashrc ]; then
    echo "export CARGO_HOME=\"$CARGO_HOME\"" >> ~/.bashrc
    echo "export RUSTUP_HOME=\"$RUSTUP_HOME\"" >> ~/.bashrc
fi
if [ -f ~/.profile ]; then
    echo "export CARGO_HOME=\"$CARGO_HOME\"" >> ~/.profile
    echo "export RUSTUP_HOME=\"$RUSTUP_HOME\"" >> ~/.profile
fi

# Try installing with prefer-binary first (uses wheels when available)
echo "Installing dependencies (preferring pre-built wheels)..."
# Use env to explicitly pass environment variables to pip and all its subprocesses
env CARGO_HOME="$CARGO_HOME" RUSTUP_HOME="$RUSTUP_HOME" pip install --prefer-binary -r requirements.txt

echo "=== Build script completed successfully ==="

