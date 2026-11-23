"""
Review script for the "Game moves" marts. Run after the build:
    python ingest/check_game_moves.py
Prints the raw values the SQL pattern-matches on, so we can confirm nothing
is silently missed, then a few sanity numbers.
"""
from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)


def show(title, sql):
    print(f"\n== {title} ==")
    print(con.sql(sql).df().to_string(index=False))


show("1) Survivor advantage events (US)",
     "select event, count(*) n from staging.stg_survivor__advantage_movement group by 1 order by 2 desc")
show("2) Survivor 'success' values on plays",
     "select success, count(*) n from staging.stg_survivor__advantage_movement "
     "where event ilike 'played%' group by 1 order by 2 desc")
show("3) Advantage types (US)",
     "select advantage_type, count(*) n from staging.stg_survivor__advantage_details group by 1 order by 2 desc limit 15")
show("4) Survivor totals",
     "select count(*) players, sum(idols_found) idols_found, sum(idol_plays) idol_plays, "
     "sum(idol_plays_cancelling_votes) plays_cancelling, sum(voted_out_holding_idol::int) out_holding_idol "
     "from marts.mart_survivor_moves")
show("5) Big Brother: labels matched per season (lowest first)",
     "select g.season_key, count(distinct g.row_label) labels, count(distinct m.label) matched "
     "from staging.stg_bigbrother__voting_grid g left join intermediate.int_bigbrother_label_map m "
     "on m.season_key = g.season_key and m.label = g.row_label where not g.is_event_row "
     "group by 1 order by matched - labels, 1 limit 8")
show("6) Big Brother: most competition wins",
     "select season_name, label, hoh_wins, veto_wins, weeks_nominated, is_winner "
     "from marts.mart_bigbrother_moves order by comp_wins desc limit 10")
show("7) Big Brother: HOH and Veto winners found per season (spot check)",
     "select season_key, sum(hoh_wins) hoh, sum(veto_wins) veto from marts.mart_bigbrother_moves "
     "group by 1 order by 1")
show("8) Big Brother: labels still unmatched, with that season's houseguests",
     "select g.season_key, g.row_label as label, "
     "(select string_agg(distinct h.houseguest_name, ', ') from staging.stg_bigbrother__houseguests h "
     " where h.season_key = g.season_key and not exists (select 1 from intermediate.int_bigbrother_label_map m2 "
     " where m2.season_key = h.season_key and m2.houseguest_name = h.houseguest_name)) as unclaimed_houseguests "
     "from (select distinct season_key, row_label from staging.stg_bigbrother__voting_grid where not is_event_row) g "
     "left join intermediate.int_bigbrother_label_map m on m.season_key = g.season_key and m.label = g.row_label "
     "where m.label is null order by 1, 2")
con.close()
