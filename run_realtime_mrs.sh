#!/bin/bash

# Realtime MRS System Launcher
# This script sets up the proper environment and runs the realtime-mrs system

# Set LSL library path for macOS
export DYLD_LIBRARY_PATH=/usr/local/lib

# Check if LSL library is installed
if [ ! -f "/usr/local/lib/liblsl.dylib" ]; then
    echo "Warning: LSL library not found. Please install with:"
    echo "brew install labstreaminglayer/tap/lsl"
    echo ""
fi

# Run the main application
echo "Starting Realtime MRS System..."
poetry run python menu.py 