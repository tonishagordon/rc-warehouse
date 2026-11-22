"""
Quick checks after building the Big Brother staging models (run after dbt build).

Usage (from the repo root):
    python ingest/check_bb_staging.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("1) Houseguests with more than one result row, and returning-player notes:\n")
con.sql("""
    SELECT season_key, houseguest_name, result_type, exit_day, prior_shows_note
    FROM staging.stg_bigbrother__houseguests
    WHERE prior_shows_note IS NOT NULL
       OR (season_key, houseguest_name) IN (
            SELECT season_key, houseguest_name
            FROM staging.stg_bigbrother__houseguests
            GROUP BY 1, 2 HAVING COUNT(*) > 1)
    ORDER BY season_key, houseguest_name
""").show(max_rows=60, max_width=220)

print("\n2) Voting cells still unclassified ('other'):\n")
con.sql("""
    SELECT season_key, voter_label, column_header, cell_value
    FROM staging.stg_bigbrother__votes
    WHERE cell_status = 'other'
    ORDER BY season_key
""").show(max_rows=40, max_width=220)

print("\n3) BB04 has 0 jury votes: its column headers and last-column cells:\n")
con.sql("""
    SELECT DISTINCT col_index, column_header, is_finale_column
    FROM staging.stg_bigbrother__voting_grid
    WHERE season_key = 'BB04'
    ORDER BY col_index
""").show(max_width=200)
con.sql("""
    SELECT row_label, value
    FROM staging.stg_bigbrother__voting_grid
    WHERE season_key = 'BB04'
      AND col_index = (SELECT MAX(col_index) FROM staging.stg_bigbrother__voting_grid WHERE season_key = 'BB04')
    ORDER BY row_label
""").show(max_rows=30, max_width=200)

print("\n4) Votes per season (eviction vs jury):\n")
con.sql("""
    SELECT season_key,
           COUNT(*) FILTER (WHERE vote_type = 'eviction') AS eviction_votes,
           COUNT(*) FILTER (WHERE vote_type = 'jury')     AS jury_votes
    FROM staging.stg_bigbrother__votes
    GROUP BY season_key ORDER BY season_key
""").show(max_rows=40)

con.close()
