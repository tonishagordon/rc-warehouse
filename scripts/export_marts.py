"""
Export the final (marts) tables to Parquet for the Streamlit app.

The app reads these small files instead of the full DuckDB warehouse, so it
can be deployed (e.g. Streamlit Community Cloud) without running the whole
pipeline. Run after `dbt build`; scripts/build_warehouse.sh does it for you.

Usage (from the repo root):
    python scripts/export_marts.py
"""

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "marts"
TABLES = ["dim_person", "dim_show", "dim_season", "fct_appearance"]

OUT_DIR.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(REPO_ROOT / "warehouse.duckdb"), read_only=True)
for table in TABLES:
    path = OUT_DIR / f"{table}.parquet"
    con.execute(f"COPY (SELECT * FROM marts.{table}) TO '{path}' (FORMAT parquet)")
    n = con.execute(f"SELECT COUNT(*) FROM marts.{table}").fetchone()[0]
    print(f"  {table:<16} {n:>6,} rows -> {path.relative_to(REPO_ROOT)}")
con.close()
