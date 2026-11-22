"""
Map the Traitors tables before modeling them.

Usage (from the repo root):
    python ingest/inspect_traitors.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("1) Tables per season:\n")
con.sql("""
    SELECT season_key, table_index, section, n_rows, n_cols, LEFT(headers, 170) AS headers
    FROM raw_traitors.wiki_tables ORDER BY season_key, table_index
""").show(max_rows=60, max_width=280)

print("\n2) Contestant table values for the columns we'll model (all seasons):\n")
con.sql("""
    WITH cast_tables AS (
        SELECT season_key, MIN(table_index) AS table_index
        FROM raw_traitors.wiki_tables
        WHERE headers ILIKE '%affiliation%' OR section ILIKE 'contestants'
        GROUP BY season_key
    )
    SELECT c.column_header, COUNT(DISTINCT c.value) AS distinct_values,
           LEFT(string_agg(DISTINCT c.value, ' | '), 400) AS sample_values
    FROM raw_traitors.wiki_cells c JOIN cast_tables USING (season_key, table_index)
    WHERE c.column_header NOT ILIKE 'contestant%' AND c.column_header NOT ILIKE 'age%'
      AND c.column_header NOT ILIKE 'from%' AND c.column_header NOT ILIKE 'hometown%'
    GROUP BY 1 ORDER BY 1
""").show(max_width=500)

con.close()
