"""
Show which kinds of tables exist across Big Brother seasons, so we can
decide which ones to model (e.g. HouseGuests, Voting history).

Usage (from the repo root):
    python ingest/inspect_bigbrother.py
"""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[1] / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

print("Table sections and how many seasons have each:\n")
con.sql("""
    SELECT section,
           COUNT(DISTINCT season_key) AS seasons,
           MIN(season_key)            AS first_season,
           MAX(season_key)            AS last_season
    FROM raw_bigbrother.wiki_tables
    GROUP BY section
    ORDER BY seasons DESC, section
""").show(max_rows=60, max_width=200)

print("\nColumn headers for the HouseGuests and Voting history tables (first 2 seasons + latest):\n")
con.sql("""
    SELECT season_key, table_index, section, n_rows, n_cols, headers
    FROM raw_bigbrother.wiki_tables
    WHERE (section ILIKE '%houseguest%' OR section ILIKE '%voting history%')
      AND season_key IN ('BB01', 'BB02', (SELECT MAX(season_key) FROM raw_bigbrother.wiki_tables))
    ORDER BY season_key, table_index
""").show(max_rows=40, max_width=400)

con.close()
