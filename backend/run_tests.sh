#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python -m pytest tests/ -v "$@"
