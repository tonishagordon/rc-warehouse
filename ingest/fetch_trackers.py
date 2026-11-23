"""
Download the watch-along trackers from Google Sheets.

Each tracker lives in Google Sheets so it can be edited from a phone or iPad.
data/manual/tracker_links.csv lists each season's "Publish to web" link
(File > Share > Publish to web > Entire document > Microsoft Excel (.xlsx)).
This script downloads each one to data/manual/<season>_tracker.xlsx, which
the normal build then loads and tests. The downloaded copy is committed, so
every build stays reproducible and git shows exactly what changed.

A file is only rewritten when its contents changed (Google's exports differ
byte-for-byte on every download even when nothing was edited).
If a download fails, the last good copy is kept and the script says so.

Usage (from the repo root):  python ingest/fetch_trackers.py
Exit code 0 always; prints CHANGED=<n> for the nightly job.
"""

import hashlib
import io
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "manual"
LINKS = MANUAL / "tracker_links.csv"


def content_hash(xlsx: bytes) -> str:
    """Fingerprint of what's IN the workbook (every sheet's cells), not the file bytes."""
    sheets = pd.read_excel(io.BytesIO(xlsx), sheet_name=None, header=None, dtype=str)
    text = "".join(f"[{name}]" + df.fillna("").to_csv(index=False, header=False)
                   for name, df in sorted(sheets.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    links = pd.read_csv(LINKS, dtype=str).fillna("")
    changed = 0
    for row in links.itertuples():
        url = row.published_xlsx_url.strip()
        dest = MANUAL / f"{row.season_key}_tracker.xlsx"
        if not url:
            print(f"  {row.season_key}: no link yet, using the copy in the repo")
            continue
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            new = resp.content
            new_hash = content_hash(new)          # also proves it's a readable workbook
        except Exception as exc:                  # keep the last good copy
            print(f"  {row.season_key}: download failed ({exc}); keeping the last good copy")
            continue
        old_hash = content_hash(dest.read_bytes()) if dest.exists() else None
        if new_hash == old_hash:
            print(f"  {row.season_key}: no changes")
            continue
        dest.write_bytes(new)
        changed += 1
        print(f"  {row.season_key}: updated from Google Sheets")
    print(f"CHANGED={changed}")


if __name__ == "__main__":
    main()
