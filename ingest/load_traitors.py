"""
LOAD: flatten the saved Traitors pages into DuckDB, one row per table cell
(same generic format and parser as Big Brother and The Challenge).

    raw_traitors.wiki_tables, raw_traitors.wiki_cells

Usage (from the repo root):
    python ingest/load_traitors.py
"""

import gzip
import json
from pathlib import Path

import duckdb
import pandas as pd

from load_bigbrother import parse_season

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "traitors"
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCHEMA = "raw_traitors"


def main() -> None:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    all_tables, all_cells = [], []
    for path in sorted((RAW_DIR / "html").glob("TR*.html.gz")):
        key = path.name.split(".")[0]
        with gzip.open(path, "rt", encoding="utf-8") as f:
            tables, cells = parse_season(key, f.read(), manifest.get(key, {}).get("fetched_at"))
        all_tables += tables
        all_cells += cells
        print(f"  {key}: {len(tables):>2} tables, {len(cells):>5,} cells")

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    for name, df in [("wiki_tables", pd.DataFrame(all_tables)), ("wiki_cells", pd.DataFrame(all_cells))]:
        con.register("df_view", df)
        con.execute(f"CREATE OR REPLACE TABLE {SCHEMA}.{name} AS SELECT * FROM df_view")
        con.unregister("df_view")
    con.close()
    print(f"\nLoaded {len(all_tables)} tables and {len(all_cells):,} cells into {SCHEMA}.")


if __name__ == "__main__":
    main()
