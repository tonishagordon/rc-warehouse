"""
Add (or update) a season's Google Sheets link in data/manual/tracker_links.csv,
then check that the link downloads.

    python ingest/add_tracker_link.py US50 survivor "https://docs.google.com/spreadsheets/d/e/.../pub?output=xlsx"

The link comes from: File > Share > Publish to web > Entire document >
Microsoft Excel (.xlsx) > Publish.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "data" / "manual" / "tracker_links.csv"


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    season_key, show, url = sys.argv[1].upper(), sys.argv[2].lower(), sys.argv[3].strip()
    if show not in {"survivor", "bigbrother"}:
        sys.exit("show must be 'survivor' or 'bigbrother'")
    if not url.startswith("https://docs.google.com/spreadsheets/d/e/"):
        sys.exit("That doesn't look like a 'Publish to web' link (it should start with "
                 "https://docs.google.com/spreadsheets/d/e/).")
    if "output=xlsx" not in url:
        sys.exit("The link must be published as Microsoft Excel (.xlsx), not as a web page. "
                 "In Publish to web, change 'Web page' to 'Microsoft Excel (.xlsx)'.")

    links = pd.read_csv(LINKS, dtype=str).fillna("") if LINKS.exists() else \
        pd.DataFrame(columns=["season_key", "show", "published_xlsx_url"])
    links = links[links["season_key"].str.match(r"^[A-Z]{2}\d+$", na=False)]   # drop stray lines
    links = links[links["season_key"] != season_key]
    links.loc[len(links)] = [season_key, show, url]
    links.sort_values("season_key").to_csv(LINKS, index=False)
    print(f"Saved the {season_key} link. Checking that it downloads...\n")

    import fetch_trackers
    fetch_trackers.main()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
