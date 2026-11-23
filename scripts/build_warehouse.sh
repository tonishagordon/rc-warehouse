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

echo "== Export marts for the app =="
cd ..
python scripts/export_marts.py

echo "== Train predictive models =="
python ml/train_challenge_return.py
python ml/train_survivor_winner.py
python ml/traitors_s5_scouting.py
