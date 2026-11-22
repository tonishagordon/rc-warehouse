"""
Review fct_appearance / dim_season after dbt build, and preview the first
cross-show analysis.

Usage (from the repo root):
    python ingest/check_appearances.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("1) Seasons by show (and any missing premiere dates):\n")
con.sql("""
    SELECT show_name, COUNT(*) AS seasons, MIN(premiered_year) AS first_year,
           MAX(premiered_year) AS last_year,
           COUNT(*) FILTER (WHERE premiered_date IS NULL) AS missing_dates
    FROM marts.dim_season GROUP BY 1 ORDER BY 1
""").show()
con.sql("""
    SELECT show_name, season_key, season_name FROM marts.dim_season
    WHERE premiered_date IS NULL ORDER BY 1, 2
""").show(max_rows=30, max_width=200)

print("\n1b) Big Brother premiere dates (should run 2000 -> 2026 in order):\n")
con.sql("""
    SELECT season_key, premiered_date, finale_date FROM marts.dim_season
    WHERE show_name = 'bigbrother' ORDER BY season_number
""").show(max_rows=30)

print("\n2) Outcome vocabulary by show (unknowns should be rare):\n")
con.sql("""
    SELECT show_name, result_category, COUNT(*) AS n
    FROM marts.fct_appearance GROUP BY 1, 2 ORDER BY 1, n DESC
""").show(max_rows=40)

print("\n3) Spot check: one person's career across shows (Cirie Fields):\n")
con.sql("""
    SELECT career_appearance_number AS n, show_name, season_name, premiered_year,
           result_category, finish_place, cast_size, finish_percentile
    FROM marts.fct_appearance f JOIN marts.dim_person p USING (person_id)
    WHERE p.person_name = 'Cirie Fields' ORDER BY n
""").show(max_width=200)

print("\n4) Preview - Feeder Show Report: how players do in their FIRST Challenge, by debut show:\n")
con.sql("""
    SELECT debut_show,
           COUNT(*) AS first_challenge_appearances,
           ROUND(AVG(finish_percentile), 3) AS avg_finish_percentile,
           SUM(CASE WHEN made_final THEN 1 ELSE 0 END) AS made_final,
           SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) AS wins
    FROM marts.fct_appearance
    WHERE show_name = 'challenge' AND show_appearance_number = 1
    GROUP BY 1 ORDER BY avg_finish_percentile DESC
""").show()

con.close()
