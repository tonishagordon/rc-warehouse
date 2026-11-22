"""
Review the first cross-show matching results (run after dbt build).

Usage (from the repo root):
    python ingest/check_matching.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)
M = "intermediate.int_challenge_origin_matches"

print("1) Challenge contestants from US Survivor/BB: did their origin season resolve?\n")
con.sql("""
    SELECT prior_shows_note AS original_season, COUNT(*) AS n
    FROM intermediate.int_person_mentions
    WHERE show_name = 'challenge'
      AND prior_shows_note SIMILAR TO '(Survivor|Big Brother).*'
      AND origin_season_key IS NULL
    GROUP BY 1 ORDER BY n DESC
""").show(max_rows=30, max_width=200)

print("\n2) Match decisions:\n")
con.sql(f"SELECT match_decision, COUNT(*) AS n FROM {M} GROUP BY 1 ORDER BY n DESC").show()

print("\n3) Everything that is NOT an auto-match (check these by eye):\n")
con.sql(f"""
    SELECT match_decision, challenge_season_key, challenge_name, origin_season_key,
           candidate_name, score, margin
    FROM {M}
    WHERE match_decision <> 'auto'
    ORDER BY match_decision, score DESC
""").show(max_rows=60, max_width=220)

print("\n4) Sample of auto-matches where the names differ (sanity check):\n")
con.sql(f"""
    SELECT challenge_name, candidate_name, origin_season_key, score, margin
    FROM {M}
    WHERE match_decision = 'auto' AND lower(challenge_name) <> lower(candidate_name)
    ORDER BY score
    LIMIT 30
""").show(max_width=200)

con.close()
