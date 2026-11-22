"""
Checks after building Challenge staging (run after dbt build).

Usage (from the repo root):
    python ingest/check_challenge_staging.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)
S = "staging.stg_challenge__contestants"

print("1) Contestants per season (look for 0s or odd counts):\n")
con.sql(f"""
    SELECT s.season_key, s.season_title, COUNT(c.contestant_key) AS contestants
    FROM staging.stg_challenge__seasons s
    LEFT JOIN {S} c USING (season_key)
    GROUP BY 1, 2 ORDER BY 1
""").show(max_rows=60, max_width=200)

print("\n2) Finish text not recognized:\n")
con.sql(f"""
    SELECT finish_raw, COUNT(*) AS n, MIN(season_key) AS example
    FROM {S} WHERE finish_type IS NULL
    GROUP BY 1 ORDER BY n DESC
""").show(max_rows=30, max_width=200)

print("\n3) Origin shows (and unclassified 'Other' / null examples):\n")
con.sql(f"""
    SELECT origin_show, COUNT(*) AS appearances, COUNT(DISTINCT contestant_name) AS people
    FROM {S} GROUP BY 1 ORDER BY appearances DESC
""").show(max_rows=30)
con.sql(f"""
    SELECT original_season, COUNT(*) AS n, MIN(season_key) AS example
    FROM {S} WHERE origin_show = 'Other' OR origin_show IS NULL
    GROUP BY 1 ORDER BY n DESC LIMIT 25
""").show(max_width=200)

print("\n4) Crossovers by origin show, US vs. international versions:\n")
con.sql(f"""
    SELECT origin_show, origin_is_us_version,
           COUNT(*) AS appearances, COUNT(DISTINCT contestant_name) AS name_variants
    FROM {S}
    WHERE origin_show IN ('Survivor', 'Big Brother', 'The Traitors')
    GROUP BY 1, 2 ORDER BY 1, 2
""").show(max_rows=120, max_width=200)

con.close()
