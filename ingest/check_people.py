"""
Review dim_person after dbt build.

Usage (from the repo root):
    python ingest/check_people.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("1) Headline numbers:\n")
con.sql("""
    SELECT COUNT(*) AS people,
           SUM(n_appearances) AS appearances,
           COUNT(*) FILTER (WHERE is_crossover) AS crossover_people,
           COUNT(*) FILTER (WHERE survivor_seasons > 1) AS survivor_returnees,
           COUNT(*) FILTER (WHERE bigbrother_seasons > 1) AS bb_returnees,
           COUNT(*) FILTER (WHERE challenge_seasons > 1) AS challenge_vets
    FROM marts.dim_person
""").show()

print("\n2) Most Challenge seasons (sanity check: Bananas, CT, Cara Maria, Wes...):\n")
con.sql("""
    SELECT person_name, challenge_seasons, shows, name_variants
    FROM marts.dim_person ORDER BY challenge_seasons DESC LIMIT 15
""").show(max_width=220)

print("\n3) Crossover people with the most total seasons:\n")
con.sql("""
    SELECT person_name, survivor_seasons, bigbrother_seasons, challenge_seasons, name_variants
    FROM marts.dim_person WHERE is_crossover
    ORDER BY n_appearances DESC LIMIT 25
""").show(max_width=220)

print("\n4) Same-season duplicates (possible over-merges, from the warn test):\n")
con.sql("""
    SELECT person_id, show_name, season_key, COUNT(*) AS n, string_agg(display_name, ' | ') AS names
    FROM marts.bridge_person_mention
    GROUP BY 1, 2, 3 HAVING COUNT(*) > 1
    ORDER BY n DESC LIMIT 20
""").show(max_width=220)

print("\n5) Review queue: possible same-person pairs NOT linked yet:\n")
con.sql("""
    SELECT show_a, season_a, name_a, show_b, season_b, name_b, ROUND(score, 3) AS score
    FROM intermediate.int_crossover_candidates
    ORDER BY score DESC
""").show(max_rows=60, max_width=220)

con.close()
