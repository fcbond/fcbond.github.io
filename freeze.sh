#!/bin/bash
set -e  # exit immediately if a command fails

# Ensure uv is installed
if ! command -v uv &>/dev/null; then
  echo "❌ uv not found. Please install it first: https://github.com/astral-sh/uv"
  exit 1
fi

# Create the virtual environment if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv .venv
fi

# Activate and run commands inside uv
echo "Installing dependencies..."
uv pip install -r requirements.txt

echo "Running freeze.py..."
uv run python freeze.py
