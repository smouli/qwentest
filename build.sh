#!/bin/bash
# Build script for Render deployment
# This script sets up the Rust/Cargo environment to use a writable directory

# Don't exit on error immediately - we want to see what's happening
# set -x  # Debug mode - show all commands (uncomment for debugging)
set -e  # Exit on error

echo "=== Starting build script ==="
echo "HOME: $HOME"
echo "PWD: $(pwd)"
echo "Python version: $(python --version 2>&1 || echo 'Python not found')"

# Force CARGO_HOME to /tmp/cargo (most reliable writable location)
export CARGO_HOME="/tmp/cargo"
export RUSTUP_HOME="/tmp/rustup"

# Also try $HOME/.cargo as backup
CARGO_HOME_ALT="$HOME/.cargo"
RUSTUP_HOME_ALT="$HOME/.rustup"

echo "CARGO_HOME: $CARGO_HOME"
echo "RUSTUP_HOME: $RUSTUP_HOME"

# Create cargo directories structure with explicit permissions
mkdir -p "$CARGO_HOME/registry/cache"
mkdir -p "$CARGO_HOME/registry/index"
mkdir -p "$CARGO_HOME/git"
mkdir -p "$CARGO_HOME/bin"
mkdir -p "$RUSTUP_HOME"

# Ensure these directories are writable
chmod -R 755 "$CARGO_HOME" 2>/dev/null || true
chmod -R 755 "$RUSTUP_HOME" 2>/dev/null || true

echo "Created Cargo directories at $CARGO_HOME"

# Create cargo config file BEFORE any cargo operations
mkdir -p "$CARGO_HOME"
cat > "$CARGO_HOME/config.toml" << EOF
[registry]
default = "crates-io"

[net]
git-fetch-with-cli = true

[build]
target-dir = "$CARGO_HOME/target"
EOF

# Check if cargo is available
if command -v cargo &> /dev/null; then
    echo "Cargo found: $(which cargo)"
    echo "Cargo version: $(cargo --version 2>&1 || echo 'unknown')"
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

# Set PIP_PREFER_BINARY to ensure pip prefers wheels
export PIP_PREFER_BINARY=1

# Try installing with prefer-binary first (uses wheels when available)
echo "Installing dependencies (preferring pre-built wheels)..."
echo "Using CARGO_HOME=$CARGO_HOME and RUSTUP_HOME=$RUSTUP_HOME"

# Create a wrapper script that ensures environment variables are set
cat > /tmp/pip_wrapper.sh << 'WRAPPER_EOF'
#!/bin/bash
export CARGO_HOME="/tmp/cargo"
export RUSTUP_HOME="/tmp/rustup"
export CARGO_TARGET_DIR="/tmp/cargo/target"
export PIP_PREFER_BINARY=1
exec pip "$@"
WRAPPER_EOF
chmod +x /tmp/pip_wrapper.sh

# Try to create symlink from system cargo location to our writable location
# This is a workaround for maturin that might hardcode paths
if [ -d "/usr/local/cargo" ] && [ ! -w "/usr/local/cargo" ]; then
    echo "Attempting to redirect /usr/local/cargo to writable location..."
    # Create parent directory structure in our writable location
    mkdir -p "$(dirname /tmp/cargo_symlink)"
    # Note: We can't create symlinks to /usr/local, but we can set CARGO_HOME
fi

# Try installing with only-binary first (most aggressive - fails if no wheels)
echo "Attempting installation with --only-binary (will fail if wheels unavailable)..."
env CARGO_HOME="$CARGO_HOME" \
    RUSTUP_HOME="$RUSTUP_HOME" \
    CARGO_TARGET_DIR="$CARGO_HOME/target" \
    PIP_PREFER_BINARY=1 \
    pip install --only-binary=:all: --no-cache-dir -r requirements.txt 2>&1 || {
    
    echo "Only-binary failed, trying with prefer-binary..."
    # Fallback to prefer-binary with explicit Cargo environment
    env CARGO_HOME="$CARGO_HOME" \
        RUSTUP_HOME="$RUSTUP_HOME" \
        CARGO_TARGET_DIR="$CARGO_HOME/target" \
        CARGO_REGISTRY_CACHE="$CARGO_HOME/registry/cache" \
        CARGO_REGISTRY_INDEX="$CARGO_HOME/registry/index" \
        PIP_PREFER_BINARY=1 \
        pip install --prefer-binary --no-cache-dir -r requirements.txt
}

echo "=== Build script completed successfully ==="

