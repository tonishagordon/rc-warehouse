"""
Explore candidate findings from the marts (run after build_warehouse.sh).
Each section is one possible story for the app / LinkedIn.

Usage (from the repo root):
    python ingest/explore_findings.py
"""

from pathlib import Path

import duckdb

M = Path(__file__).resolve().parents[1] / "data" / "marts"
con = duckdb.connect()
for t in ["dim_person", "dim_season", "fct_appearance"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{M / (t + '.parquet')}')")


def show(title, sql, rows=40):
    print(f"\n{'=' * 100}\n{title}\n{'=' * 100}")
    con.sql(sql).show(max_rows=rows, max_width=220)


show("A) CASTING SHIFT: where Challenge casts come from, by era (share of appearances)", """
    WITH c AS (
        SELECT CASE
                 WHEN f.premiered_year < 2005 THEN '1998-2004'
                 WHEN f.premiered_year < 2011 THEN '2005-2010'
                 WHEN f.premiered_year < 2017 THEN '2011-2016'
                 WHEN f.premiered_year < 2022 THEN '2017-2021'
                 ELSE '2022-2026' END AS era,
               CASE WHEN p.background IN ('The Real World', 'Road Rules', 'The Challenge')
                    THEN 'MTV originals (Real World / Road Rules / Fresh Meat)'
                    WHEN p.background IN ('Survivor', 'Big Brother') THEN 'Survivor / Big Brother'
                    WHEN p.background IN ('Are You the One?', 'Love Island', 'Ex on the Beach', 'Too Hot to Handle')
                    THEN 'Dating shows'
                    ELSE 'Other / international' END AS source
        FROM fct_appearance f JOIN dim_person p USING (person_id)
        WHERE f.show_name = 'challenge'
    )
    SELECT era,
           COUNT(*) AS appearances,
           ROUND(AVG((source LIKE 'MTV%')::INT), 2)           AS mtv_originals,
           ROUND(AVG((source = 'Survivor / Big Brother')::INT), 2) AS survivor_bb,
           ROUND(AVG((source = 'Dating shows')::INT), 2)      AS dating_shows,
           ROUND(AVG((source LIKE 'Other%')::INT), 2)         AS other
    FROM c GROUP BY era ORDER BY era
""")

show("B) THE RETURN TICKET: does how you do in your first Challenge decide whether you're invited back?", """
    WITH rookies AS (
        SELECT f.person_id, f.finish_percentile, f.is_winner, f.made_final, p.challenge_seasons
        FROM fct_appearance f JOIN dim_person p USING (person_id)
        WHERE f.show_name = 'challenge' AND f.show_appearance_number = 1
          AND f.premiered_year <= 2023          -- give everyone time to be re-cast
          AND f.finish_percentile IS NOT NULL
    )
    SELECT CASE WHEN is_winner THEN '1. Won'
                WHEN made_final THEN '2. Made the final'
                WHEN finish_percentile >= 0.5 THEN '3. Top half'
                ELSE '4. Bottom half' END AS first_season_result,
           COUNT(*) AS rookies,
           ROUND(AVG((challenge_seasons > 1)::INT), 2) AS returned_rate,
           ROUND(AVG(challenge_seasons), 1) AS avg_career_seasons
    FROM rookies GROUP BY 1 ORDER BY 1
""")

show("B2) Return rate by background (rookies through 2023, 10+ players)", """
    SELECT p.background, COUNT(*) AS rookies,
           ROUND(AVG((p.challenge_seasons > 1)::INT), 2) AS returned_rate,
           ROUND(AVG(p.challenge_seasons), 1) AS avg_career_seasons
    FROM fct_appearance f JOIN dim_person p USING (person_id)
    WHERE f.show_name = 'challenge' AND f.show_appearance_number = 1 AND f.premiered_year <= 2023
    GROUP BY 1 HAVING COUNT(*) >= 10 ORDER BY returned_rate DESC
""")

show("C) THE EXPERIENCE CURVE: same people, 1st vs 2nd vs 3rd season on a show (people with 3+ seasons there)", """
    WITH vets AS (
        SELECT person_id, show_name FROM fct_appearance
        GROUP BY 1, 2 HAVING COUNT(*) >= 3
    )
    SELECT f.show_name,
           COUNT(DISTINCT f.person_id) AS people,
           ROUND(AVG(f.finish_percentile) FILTER (WHERE f.show_appearance_number = 1), 3) AS season_1,
           ROUND(AVG(f.finish_percentile) FILTER (WHERE f.show_appearance_number = 2), 3) AS season_2,
           ROUND(AVG(f.finish_percentile) FILTER (WHERE f.show_appearance_number = 3), 3) AS season_3,
           ROUND(AVG(f.finish_percentile) FILTER (WHERE f.show_appearance_number BETWEEN 4 AND 6), 3) AS seasons_4_6,
           ROUND(AVG(f.finish_percentile) FILTER (WHERE f.show_appearance_number > 6), 3) AS seasons_7_plus
    FROM fct_appearance f JOIN vets USING (person_id, show_name)
    GROUP BY 1 ORDER BY 1
""")

show("D) HOME FIELD ADVANTAGE: crossover players on their debut show vs. on other shows", """
    WITH x AS (
        SELECT f.person_id,
               AVG(f.finish_percentile) FILTER (WHERE f.show_name = f.debut_show)  AS home,
               AVG(f.finish_percentile) FILTER (WHERE f.show_name <> f.debut_show) AS away
        FROM fct_appearance f JOIN dim_person p USING (person_id)
        WHERE p.is_crossover
        GROUP BY 1
    )
    SELECT COUNT(*) AS crossover_people,
           ROUND(AVG(home), 3) AS avg_on_debut_show,
           ROUND(AVG(away), 3) AS avg_on_other_shows,
           SUM((home > away)::INT) AS did_better_at_home,
           SUM((away > home)::INT) AS did_better_away
    FROM x WHERE home IS NOT NULL AND away IS NOT NULL
""")

show("D2) ...split by debut show", """
    WITH x AS (
        SELECT f.person_id, ANY_VALUE(f.debut_show) AS debut_show,
               AVG(f.finish_percentile) FILTER (WHERE f.show_name = f.debut_show)  AS home,
               AVG(f.finish_percentile) FILTER (WHERE f.show_name <> f.debut_show) AS away
        FROM fct_appearance f JOIN dim_person p USING (person_id)
        WHERE p.is_crossover GROUP BY 1
    )
    SELECT debut_show, COUNT(*) AS people, ROUND(AVG(home), 3) AS home, ROUND(AVG(away), 3) AS away
    FROM x WHERE home IS NOT NULL AND away IS NOT NULL GROUP BY 1 ORDER BY people DESC
""")

show("E) CHAMPIONS ABROAD: people who won a season, then tried a different show (their first try there)", """
    WITH first_win AS (
        SELECT person_id, MIN(premiered_date) AS first_win_date
        FROM fct_appearance WHERE is_winner GROUP BY 1
    ),
    tries AS (
        SELECT f.*, ROW_NUMBER() OVER (PARTITION BY f.person_id, f.show_name ORDER BY f.premiered_date) AS n
        FROM fct_appearance f JOIN first_win w USING (person_id)
        WHERE f.premiered_date > w.first_win_date
          AND f.show_name NOT IN (SELECT show_name FROM fct_appearance g
                                  WHERE g.person_id = f.person_id AND g.is_winner
                                    AND g.premiered_date = w.first_win_date)
    )
    SELECT COUNT(*) AS new_show_debuts_by_champions,
           ROUND(AVG(finish_percentile), 3) AS avg_finish_percentile,
           SUM(made_final::INT) AS made_final,
           SUM(is_winner::INT) AS won_again
    FROM tries WHERE n = 1
""")

show("E2) ...the champions themselves", """
    WITH first_win AS (
        SELECT person_id, MIN(premiered_date) AS d, ANY_VALUE(show_name) AS won_on
        FROM fct_appearance WHERE is_winner GROUP BY 1
    ),
    tries AS (
        SELECT f.*, w.won_on,
               ROW_NUMBER() OVER (PARTITION BY f.person_id, f.show_name ORDER BY f.premiered_date) AS n
        FROM fct_appearance f JOIN first_win w USING (person_id)
        WHERE f.premiered_date > w.d AND f.show_name <> w.won_on
    )
    SELECT p.person_name, t.won_on, t.season_name AS then_played, t.result_category, t.finish_percentile
    FROM tries t JOIN dim_person p USING (person_id)
    WHERE n = 1 ORDER BY t.finish_percentile DESC NULLS LAST
""", rows=60)

show("F) THE TRAITORS: who actually wins, Traitors or Faithful?", """
    SELECT season_name, game_role, COUNT(*) AS winners
    FROM fct_appearance WHERE show_name = 'traitors' AND is_winner
    GROUP BY 1, 2 ORDER BY 1, 2
""")

show("G) LONGEST CAREERS: span from first to latest season, any show", """
    SELECT p.person_name, p.shows, p.n_appearances,
           MIN(f.premiered_year) AS first_year, MAX(f.premiered_year) AS latest_year,
           MAX(f.premiered_year) - MIN(f.premiered_year) AS years_on_tv,
           SUM(f.is_winner::INT) AS wins
    FROM fct_appearance f JOIN dim_person p USING (person_id)
    GROUP BY p.person_name, p.shows, p.n_appearances
    ORDER BY years_on_tv DESC, n_appearances DESC LIMIT 15
""")

con.close()
