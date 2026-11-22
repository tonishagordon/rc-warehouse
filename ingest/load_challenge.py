"""
LOAD: flatten the saved Challenge pages into DuckDB, one row per table cell
(the same generic format as Big Brother, reusing its parser).

    raw_challenge.season_index  the season list from season_index.csv
    raw_challenge.wiki_tables   one row per table (section, caption, headers)
    raw_challenge.wiki_cells    one row per cell

Usage (from the repo root):
    python ingest/load_challenge.py
"""

import gzip
import json
from pathlib import Path

import duckdb
import pandas as pd

from load_bigbrother import parse_season

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "challenge"
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCHEMA = "raw_challenge"


def main() -> None:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    index_df = pd.read_csv(RAW_DIR / "season_index.csv", dtype=str)

    all_tables, all_cells = [], []
    for path in sorted((RAW_DIR / "html").glob("*.html.gz")):
        key = path.name.split(".")[0]
        with gzip.open(path, "rt", encoding="utf-8") as f:
            tables, cells = parse_season(key, f.read(), manifest.get(key, {}).get("fetched_at"))
        all_tables += tables
        all_cells += cells
        print(f"  {key:<11} {len(tables):>2} tables, {len(cells):>6,} cells")

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    for name, df in [("season_index", index_df),
                     ("wiki_tables", pd.DataFrame(all_tables)),
                     ("wiki_cells", pd.DataFrame(all_cells))]:
        con.register("df_view", df)
        con.execute(f"CREATE OR REPLACE TABLE {SCHEMA}.{name} AS SELECT * FROM df_view")
        con.unregister("df_view")
    con.close()
    print(f"\nLoaded {len(all_tables):,} tables and {len(all_cells):,} cells into {SCHEMA}.")


if __name__ == "__main__":
    main()
