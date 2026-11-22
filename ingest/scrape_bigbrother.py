"""
EXTRACT: download Big Brother (US) season pages from Wikipedia.

Saves one gzipped HTML snapshot per season, plus a manifest recording
when each page was fetched and which revision it came from. Parsing happens
separately in load_bigbrother.py, so pages never need to be re-downloaded
just to change parsing logic.

Usage (from the repo root):
    python ingest/scrape_bigbrother.py                # seasons 1-28, skips ones already saved
    python ingest/scrape_bigbrother.py --refresh 28   # re-download specific seasons (e.g. the latest)

Source: Wikipedia (CC BY-SA 4.0). Requests are rate-limited and identify
this project via the User-Agent, per Wikimedia's API etiquette.
"""

import argparse
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "raw" / "bigbrother" / "html"
MANIFEST = REPO_ROOT / "data" / "raw" / "bigbrother" / "manifest.json"

API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    # Wikimedia asks API clients to identify themselves. Put your GitHub URL here.
    "User-Agent": "rc-warehouse/0.1 (https://github.com/tonishagordon/rc-warehouse) portfolio project"
}
FIRST_SEASON, LAST_SEASON = 1, 28
PAUSE_SECONDS = 1.5


def page_title(season: int) -> str:
    return f"Big Brother {season} (American season)"


def fetch(title: str) -> dict:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text|revid",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{data['error'].get('code')}: {data['error'].get('info')}")
    return data["parse"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", type=int, nargs="*", default=[],
                    help="season numbers to re-download even if already saved")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    for season in range(FIRST_SEASON, LAST_SEASON + 1):
        key = f"BB{season:02d}"
        path = OUT_DIR / f"{key}.html.gz"
        if path.exists() and season not in args.refresh:
            print(f"  {key}: already saved, skipping")
            continue

        title = page_title(season)
        try:
            parsed = fetch(title)
        except Exception as exc:  # keep going; one bad page shouldn't stop the run
            print(f"  {key}: FAILED ({exc})")
            continue

        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(parsed["text"])

        manifest[key] = {
            "season": season,
            "title": parsed.get("title", title),
            "revid": parsed.get("revid"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "file": path.name,
        }
        print(f"  {key}: saved ({path.stat().st_size / 1024:,.0f} KB, rev {parsed.get('revid')})")
        time.sleep(PAUSE_SECONDS)

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {len(manifest)} seasons -> {MANIFEST.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
