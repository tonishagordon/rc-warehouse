"""
Map the Challenge tables: which sections exist across seasons, and what the
contestant and elimination tables look like in an early, middle and recent season.

Usage (from the repo root):
    python ingest/inspect_challenge.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("Sections appearing in 3+ seasons:\n")
con.sql("""
    SELECT section, COUNT(DISTINCT season_key) AS seasons,
           MIN(season_key) AS first, MAX(season_key) AS last
    FROM raw_challenge.wiki_tables
    WHERE season_key <> 'CONTESTANTS'
    GROUP BY section HAVING COUNT(DISTINCT season_key) >= 3
    ORDER BY seasons DESC
""").show(max_rows=40, max_width=200)

print("\nSeasons with NO contestant/cast table section (need a look):\n")
con.sql("""
    SELECT i.season_key, i.title
    FROM raw_challenge.season_index i
    WHERE i.season_key NOT IN (
        SELECT season_key FROM raw_challenge.wiki_tables
        WHERE section ILIKE '%contestant%' OR section ILIKE '%cast%')
    ORDER BY i.season_key
""").show(max_rows=60, max_width=200)

print("\nTable headers in sample seasons (early / middle / latest main season):\n")
con.sql("""
    WITH latest AS (SELECT MAX(season_key) AS k FROM raw_challenge.wiki_tables WHERE season_key LIKE 'CH__')
    SELECT season_key, table_index, section, n_rows, n_cols, LEFT(headers, 220) AS headers
    FROM raw_challenge.wiki_tables
    WHERE season_key IN ('CH05', 'CH25', (SELECT k FROM latest))
    ORDER BY season_key, table_index
""").show(max_rows=40, max_width=400)

print("\nContestants list page tables:\n")
con.sql("""
    SELECT table_index, section, n_rows, n_cols, LEFT(headers, 200) AS headers
    FROM raw_challenge.wiki_tables
    WHERE season_key = 'CONTESTANTS'
    ORDER BY table_index
""").show(max_rows=20, max_width=400)

con.close()
