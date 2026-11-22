"""
EXTRACT: download every Challenge season page listed in season_index.csv,
plus Wikipedia's "List of The Challenge (TV series) contestants" page
(which records each contestant's original show, a key input for
cross-show matching).

Same approach as Big Brother: gzipped snapshots + a manifest of revision IDs.

Usage (from the repo root):
    python ingest/scrape_challenge.py                 # skips pages already saved
    python ingest/scrape_challenge.py --refresh CH42  # re-download specific keys
"""

import argparse
import csv
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scrape_bigbrother import fetch, PAUSE_SECONDS

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "challenge"
HTML_DIR = RAW_DIR / "html"
INDEX_CSV = RAW_DIR / "season_index.csv"
MANIFEST = RAW_DIR / "manifest.json"

EXTRA_PAGES = {"CONTESTANTS": "List of The Challenge (TV series) contestants"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", nargs="*", default=[], help="season keys to re-download")
    args = ap.parse_args()

    if not INDEX_CSV.exists():
        raise SystemExit("Run discover_challenge.py first.")
    with open(INDEX_CSV, encoding="utf-8") as f:
        pages = {r["season_key"]: r["page_title"] for r in csv.DictReader(f)
                 if r.get("include", "Y").strip().upper() == "Y"}
    pages.update(EXTRA_PAGES)

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    failed = []

    for key, title in pages.items():
        path = HTML_DIR / f"{key}.html.gz"
        if path.exists() and key not in args.refresh:
            print(f"  {key:<11} already saved, skipping")
            continue
        try:
            parsed = fetch(title)
        except Exception as exc:
            print(f"  {key:<11} FAILED ({exc})  [{title}]")
            failed.append(key)
            continue
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(parsed["text"])
        manifest[key] = {
            "title": parsed.get("title", title),
            "revid": parsed.get("revid"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "file": path.name,
        }
        print(f"  {key:<11} saved ({path.stat().st_size / 1024:,.0f} KB)  {parsed.get('title', title)}")
        time.sleep(PAUSE_SECONDS)

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {len(manifest)} pages. Failed: {failed or 'none'}")


if __name__ == "__main__":
    main()
