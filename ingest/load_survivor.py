"""
Load the survivoR Excel export into DuckDB as raw tables.

Usage (from the repo root):
    python ingest/load_survivor.py

Expects:  data/raw/survivor/survivoR.xlsx
Creates:  warehouse.duckdb  with schema raw_survivor (one table per sheet)
"""

from datetime import datetime, timezone
from pathlib import Path
import re

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = REPO_ROOT / "data" / "raw" / "survivor" / "survivoR.xlsx"
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCHEMA = "raw_survivor"


def clean_name(name: str) -> str:
    """Turn a sheet or column name into a safe snake_case identifier."""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()
    return name or "unnamed"


def main() -> None:
    if not XLSX_PATH.exists():
        raise SystemExit(f"Missing file: {XLSX_PATH}\nDownload survivoR.xlsx first.")

    sheets = pd.read_excel(XLSX_PATH, sheet_name=None)  # dict of {sheet: DataFrame}
    loaded_at = datetime.now(timezone.utc).isoformat()

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    print(f"Loading {len(sheets)} sheets into {DB_PATH.name}:{SCHEMA}\n")
    for sheet_name, df in sheets.items():
        table = clean_name(sheet_name)
        df.columns = [clean_name(c) for c in df.columns]
        df["_source_file"] = XLSX_PATH.name
        df["_loaded_at"] = loaded_at

        con.register("df_view", df)
        con.execute(f"CREATE OR REPLACE TABLE {SCHEMA}.{table} AS SELECT * FROM df_view")
        con.unregister("df_view")
        print(f"  {SCHEMA}.{table:<28} {len(df):>7,} rows  {len(df.columns):>3} cols")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
