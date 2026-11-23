"""
Look at the raw survivoR tables the Survivor winner model will use, so its
feature SQL is written against the real columns.

Usage (from the repo root):
    python ingest/inspect_survivor_ml.py
"""

from pathlib import Path

import duckdb

con = duckdb.connect(str(Path(__file__).resolve().parents[1] / "warehouse.duckdb"), read_only=True)

print("confessionals columns:")
print("  " + ", ".join(r[0] for r in con.execute(
    "select column_name from information_schema.columns "
    "where table_schema='raw_survivor' and table_name='confessionals' order by ordinal_position").fetchall()))
con.sql("select * from raw_survivor.confessionals where version='US' and season=50 limit 3").show(max_width=250)

print("\ntribe_status values:")
con.sql("select tribe_status, count(*) n from raw_survivor.tribe_mapping where version='US' group by 1 order by 2 desc").show()

print("\nUS51 data available so far (episodes per table):")
for t in ["episodes", "confessionals", "vote_history", "challenge_results", "tribe_mapping", "castaways"]:
    n = con.execute(f"select count(distinct episode) from raw_survivor.{t} where version_season='US51'").fetchone()[0] \
        if t != "castaways" else con.execute("select count(*) from raw_survivor.castaways where version_season='US51'").fetchone()[0]
    print(f"  {t:<18} {n}")
con.close()
