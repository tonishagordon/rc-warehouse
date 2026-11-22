"""
EXTRACT: download The Traitors (US) season pages from Wikipedia.

Same pattern as Big Brother: gzipped snapshots + a manifest of revision IDs.
The Traitors is the 4th show, added to show the model takes a new source
without redesign (docs/decisions.md D013).

Usage (from the repo root):
    python ingest/scrape_traitors.py                 # seasons 1-4, skips ones already saved
    python ingest/scrape_traitors.py --refresh 5     # e.g. add/refresh a new season
"""

import argparse
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scrape_bigbrother import fetch, PAUSE_SECONDS

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "traitors"
HTML_DIR = RAW_DIR / "html"
MANIFEST = RAW_DIR / "manifest.json"
SEASONS = range(1, 5)   # US seasons 1-4 (season 5 airs 2027)


def page_title(season: int) -> str:
    return f"The Traitors (American TV series) season {season}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", type=int, nargs="*", default=[])
    args = ap.parse_args()

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    seasons = sorted(set(SEASONS) | set(args.refresh))

    for season in seasons:
        key = f"TR{season:02d}"
        path = HTML_DIR / f"{key}.html.gz"
        if path.exists() and season not in args.refresh:
            print(f"  {key}: already saved, skipping")
            continue
        try:
            parsed = fetch(page_title(season))
        except Exception as exc:
            print(f"  {key}: FAILED ({exc})")
            continue
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(parsed["text"])
        manifest[key] = {
            "season": season,
            "title": parsed.get("title"),
            "revid": parsed.get("revid"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "file": path.name,
        }
        print(f"  {key}: saved ({path.stat().st_size / 1024:,.0f} KB)  {parsed.get('title')}")
        time.sleep(PAUSE_SECONDS)

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {len(manifest)} seasons")


if __name__ == "__main__":
    main()
