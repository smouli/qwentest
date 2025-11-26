#!/bin/bash
# Build script for Render deployment
# This script sets up the Rust/Cargo environment to use a writable directory

set -e  # Exit on error

# Set CARGO_HOME to a writable directory in the project
export CARGO_HOME="$HOME/.cargo"
export RUSTUP_HOME="$HOME/.rustup"

# Create cargo directories if they don't exist
mkdir -p "$CARGO_HOME/registry/cache"
mkdir -p "$CARGO_HOME/registry/index"
mkdir -p "$RUSTUP_HOME"

# Upgrade pip first
pip install --upgrade pip

# Install dependencies
# The CARGO_HOME environment variable will ensure Rust packages are installed in a writable location
pip install -r requirements.txt

