#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

pyinstaller -F -n JournalApp app.py \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "data:data"
