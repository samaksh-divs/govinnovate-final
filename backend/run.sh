#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python -m venv .venv; fi
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install -q -r requirements.txt
uvicorn app.main:app --reload --port 8000
