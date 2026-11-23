"""
Load every watch-along tracker in data/manual/*_tracker.xlsx into the
raw_manual schema (alliances, votes, showmances), tagged with show and season.

Tables are always created, even with no trackers yet, so dbt always builds.
Usage (from the repo root): python ingest/load_manual.py
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "manual"
COLUMNS = {
    "alliances": ["alliance_name", "member", "episode_joined", "episode_left", "notes"],
    "votes": ["episode", "planned_target", "voted_out", "blindside", "ran_the_vote", "notes"],
    "showmances": ["player_1", "player_2", "episode_started", "episode_ended", "notes"],
}


def read_tracker(path: Path) -> dict[str, pd.DataFrame]:
    meta = pd.read_excel(path, sheet_name="How to use", header=None, dtype=str)
    show, season_key = meta.iat[0, 1], meta.iat[1, 1]          # B1 = show, B2 = season_key
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    out = {}
    for table, cols in COLUMNS.items():
        df = sheets.get(table.capitalize(), pd.DataFrame(columns=cols)).reindex(columns=cols)
        df = df.dropna(how="all")
        df.insert(0, "season_key", season_key)
        df.insert(0, "show_name", show)
        df.insert(2, "source_row", df.index + 2)  # Excel row number, for error messages
        df.insert(3, "source_file", path.name)
        out[table] = df
    return out


def main() -> None:
    frames = {t: [] for t in COLUMNS}
    files = sorted(SRC.glob("*_tracker.xlsx")) if SRC.exists() else []
    for f in files:
        for table, df in read_tracker(f).items():
            frames[table].append(df)
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"))
    con.execute("create schema if not exists raw_manual")
    for table, cols in COLUMNS.items():
        empty = pd.DataFrame(columns=["show_name", "season_key", "source_row", "source_file"] + cols)
        df = pd.concat(frames[table], ignore_index=True) if frames[table] else empty
        df = df.astype({c: "string" for c in df.columns if c != "source_row"})
        con.register("df", df)
        con.execute(f"create or replace table raw_manual.{table} as select * from df")
        con.unregister("df")
        print(f"  raw_manual.{table:<11} {len(df):>4} rows")
    con.close()
    print(f"Loaded {len(files)} tracker file(s).")


if __name__ == "__main__":
    main()
