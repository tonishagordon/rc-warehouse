"""
Checks after adding The Traitors (run after dbt build).

Usage (from the repo root):
    python ingest/check_traitors.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("1) Traitors seasons:\n")
con.sql("""
    SELECT season_key, season_name, premiered_date, cast_size, is_season_complete
    FROM marts.dim_season WHERE show_name = 'traitors' ORDER BY season_key
""").show()

print("\n2) Finish text not recognized (should be empty):\n")
con.sql("""
    SELECT season_key, contestant_name, finish_raw
    FROM staging.stg_traitors__contestants WHERE finish_type IS NULL
""").show(max_width=200)

print("\n3) Origin-season matches for Traitors players (Survivor / Big Brother):\n")
con.sql("""
    SELECT source_season_key, source_name, origin_season_key, candidate_name, match_decision, score
    FROM intermediate.int_origin_matches WHERE source_show = 'traitors'
    ORDER BY source_season_key, source_name
""").show(max_rows=60, max_width=200)

print("\n4) Traitors players linked to other shows in this warehouse:\n")
con.sql("""
    SELECT p.person_name, p.survivor_seasons, p.bigbrother_seasons, p.challenge_seasons,
           p.traitors_seasons
    FROM marts.dim_person p
    WHERE p.traitors_seasons > 0 AND p.is_crossover
    ORDER BY p.n_appearances DESC
""").show(max_rows=60, max_width=200)

print("\n5) Traitors players whose notability names a show we have, but who are NOT linked:\n")
con.sql("""
    SELECT f.season_key, f.name_as_billed, t.notability
    FROM marts.fct_appearance f
    JOIN marts.dim_person p USING (person_id)
    JOIN staging.stg_traitors__contestants t
      ON f.season_key = t.season_key AND f.name_as_billed = t.contestant_name
    WHERE f.show_name = 'traitors' AND NOT p.is_crossover
      AND (t.origin_show IN ('Survivor', 'Big Brother', 'The Challenge', 'The Real World',
                             'Road Rules', 'Are You the One?', 'Ex on the Beach')
           OR t.notability ILIKE '%challenge%')
    ORDER BY 1, 2
""").show(max_rows=40, max_width=200)

print("\n6) Review queue (new pairs from the Traitors data):\n")
con.sql("""
    SELECT show_a, season_a, name_a, show_b, season_b, name_b, ROUND(score, 3) AS score
    FROM intermediate.int_crossover_candidates ORDER BY score DESC
""").show(max_rows=40, max_width=220)

print("\n7) Preview - The Strategist Penalty: Traitors outcomes by where players came from:\n")
con.sql("""
    WITH t AS (
        SELECT f.*, CASE WHEN p.survivor_seasons + p.bigbrother_seasons > 0
                         THEN 'Survivor / Big Brother alum' ELSE 'Everyone else' END AS background
        FROM marts.fct_appearance f JOIN marts.dim_person p USING (person_id)
        WHERE f.show_name = 'traitors'
    )
    SELECT background,
           COUNT(*) AS players,
           ROUND(AVG(finish_percentile), 3) AS avg_finish_percentile,
           ROUND(AVG(CASE WHEN game_role = 'Traitor' THEN 1 ELSE 0 END), 3) AS traitor_rate,
           ROUND(AVG(CASE WHEN exit_method = 'banished' THEN 1 ELSE 0 END), 3) AS banished_rate,
           ROUND(AVG(CASE WHEN exit_method = 'murdered' THEN 1 ELSE 0 END), 3) AS murdered_rate,
           SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) AS wins
    FROM t GROUP BY 1
""").show()

con.close()
