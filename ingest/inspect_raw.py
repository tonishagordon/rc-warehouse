"""
Print the columns of the raw Survivor tables we'll model first,
so staging models can be written against the real column names.

Usage (from the repo root):
    python ingest/inspect_raw.py
"""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[1] / "warehouse.duckdb"
SCHEMA = "raw_survivor"
TABLES = [
    "season_summary",
    "castaways",
    "castaway_details",
    "episodes",
    "boot_order",
    "vote_history",
    "jury_votes",
    "challenge_results",
    "tribe_mapping",
    "advantage_movement",
]

con = duckdb.connect(str(DB_PATH), read_only=True)

print("Versions in castaways (show franchises):")
for version, n in con.execute(
    f"SELECT version, COUNT(*) FROM {SCHEMA}.castaways GROUP BY 1 ORDER BY 2 DESC"
).fetchall():
    print(f"  {version}: {n}")

for table in TABLES:
    cols = con.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [SCHEMA, table],
    ).fetchall()
    print(f"\n{table}:")
    print("  " + ", ".join(f"{c} ({t.lower()})" for c, t in cols if not c.startswith("_")))

con.close()
