#!/bin/bash

# Create the virtual environment if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv .venv
fi
uv pip install -r requirements.txt 

uv run python wsgi.py
