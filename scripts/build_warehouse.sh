#!/usr/bin/env bash
# Rebuild the whole warehouse from the raw snapshots committed in data/raw/.
# No network needed: scraping is a separate, occasional step (ingest/scrape_*.py).
#
# Usage (from the repo root):  bash scripts/build_warehouse.sh
set -euo pipefail

echo "== Load raw data =="
python ingest/load_survivor.py
python ingest/load_bigbrother.py
python ingest/load_challenge.py
python ingest/load_traitors.py

echo "== Transform + test (dbt) =="
cd dbt
dbt build
