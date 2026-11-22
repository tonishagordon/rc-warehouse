"""
Show the row labels used in Big Brother "Voting history" tables, split into
houseguest vote rows (label matches a houseguest's first name) and event rows
(Head of Household, Nominations, Evicted...). Run after `dbt build`.

Usage (from the repo root):
    python ingest/inspect_bb_voting.py
"""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[1] / "warehouse.duckdb"
con = duckdb.connect(str(DB_PATH), read_only=True)

LABELS = """
    WITH vt AS (
        SELECT season_key, MIN(table_index) AS table_index
        FROM raw_bigbrother.wiki_tables
        WHERE section = 'Voting history'
        GROUP BY season_key
    ),
    labels AS (
        SELECT c.season_key, c.row_index, c.value AS label
        FROM raw_bigbrother.wiki_cells c
        JOIN vt USING (season_key, table_index)
        WHERE c.col_index = 0
    ),
    hg AS (
        SELECT season_key, LOWER(SPLIT_PART(houseguest_name, ' ', 1)) AS first_name
        FROM staging.stg_bigbrother__houseguests
    )
    SELECT l.*, (hg.first_name IS NOT NULL) AS is_houseguest_row
    FROM labels l
    LEFT JOIN hg
      ON l.season_key = hg.season_key
     AND LOWER(SPLIT_PART(l.label, ' ', 1)) = hg.first_name
"""

print("Event-row labels (not a houseguest) and how many seasons use each:\n")
con.sql(f"""
    SELECT label, COUNT(DISTINCT season_key) AS seasons
    FROM ({LABELS})
    WHERE NOT is_houseguest_row
    GROUP BY label ORDER BY seasons DESC, label
""").show(max_rows=80, max_width=200)

print("\nHouseguest-matched rows per season vs. houseguest count:\n")
con.sql(f"""
    SELECT l.season_key,
           COUNT(*) FILTER (WHERE is_houseguest_row) AS matched_rows,
           (SELECT COUNT(*) FROM staging.stg_bigbrother__houseguests h
             WHERE h.season_key = l.season_key)      AS houseguests
    FROM ({LABELS}) l
    GROUP BY l.season_key ORDER BY l.season_key
""").show(max_rows=40)

print("\nBB28 voting history, first 4 columns, as a sample of the grid:\n")
con.sql("""
    WITH vt AS (
        SELECT MIN(table_index) AS t FROM raw_bigbrother.wiki_tables
        WHERE season_key = 'BB28' AND section = 'Voting history'
    )
    SELECT row_index,
           MAX(value) FILTER (WHERE col_index = 0) AS label,
           MAX(value) FILTER (WHERE col_index = 1) AS col_1,
           MAX(value) FILTER (WHERE col_index = 2) AS col_2,
           MAX(value) FILTER (WHERE col_index = 3) AS col_3
    FROM raw_bigbrother.wiki_cells
    WHERE season_key = 'BB28' AND table_index = (SELECT t FROM vt)
    GROUP BY row_index ORDER BY row_index
""").show(max_rows=40, max_width=200)

con.close()
