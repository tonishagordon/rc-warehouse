"""
Create a blank watch-along tracker workbook for one season.

    python ingest/make_tracker.py survivor US51
    python ingest/make_tracker.py bigbrother BB03

Writes data/manual/<season>_tracker.xlsx with:
  - How to use   : short instructions
  - Cast         : names exactly as the warehouse knows them (feeds the dropdowns)
  - Alliances    : one row per alliance member
  - Votes        : one row per Tribal Council / eviction: the plan vs. what happened
  - Showmances   : Big Brother only
Never overwrites an existing tracker (your entries are safe).
"""

import sys
from pathlib import Path

import duckdb
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "manual"
HEADER_FILL = PatternFill("solid", fgColor="242422")
HEADER_FONT = Font(bold=True, color="F0EFEC")
ROWS = 300  # rows with dropdowns ready to fill

CAST_SQL = {
    "survivor": """select distinct castaway_short_name as name, full_name as full_name
                   from staging.stg_survivor__castaways where season_key = ? order by 1""",
    "bigbrother": """select distinct m.label as name, m.houseguest_name as full_name
                     from intermediate.int_bigbrother_label_map m where m.season_key = ? order by 1""",
}

SHEETS = {
    "Alliances": [("alliance_name", 24), ("member", 22), ("episode_joined", 15), ("episode_left", 14), ("notes", 50)],
    "Votes": [("episode", 10), ("planned_target", 22), ("voted_out", 22), ("blindside", 11),
              ("ran_the_vote", 22), ("notes", 50)],
    "Showmances": [("player_1", 22), ("player_2", 22), ("episode_started", 16), ("episode_ended", 15), ("notes", 50)],
}

HOW_TO = [
    "How to use this tracker",
    "",
    "Fill it in as you watch. Leave cells blank when you don't know yet; never delete the header row.",
    "Names: pick from the dropdowns (they come from the Cast tab, so they always match the warehouse).",
    "Episodes: Survivor = episode number. Big Brother = week number.",
    "",
    "Alliances: one row per member. Same alliance name on every row for that alliance.",
    "   episode_left is blank while they're still together.",
    "Votes: one row per Tribal Council or eviction.",
    "   planned_target = who the majority meant to send home. voted_out = who actually left.",
    "   blindside = Yes if the person voted out didn't see it coming.",
    "   ran_the_vote = the player who drove the plan (optional).",
    "Showmances (Big Brother): one row per couple.",
    "",
    "In Google Sheets, changes are picked up overnight and the live app updates on its own.",
    "The build checks every row (unknown names, an alliance that ends before it starts, ...).",
    "If something is off, the nightly run on GitHub (Actions tab) names the sheet and row to fix.",
]


def main(show: str, season_key: str) -> None:
    if show not in CAST_SQL:
        sys.exit("show must be 'survivor' or 'bigbrother'")
    path = OUT / f"{season_key}_tracker.xlsx"
    if path.exists():
        sys.exit(f"{path.relative_to(ROOT)} already exists; not overwriting your entries.")

    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    cast = con.execute(CAST_SQL[show], [season_key]).fetchall()
    con.close()
    if not cast:
        sys.exit(f"No cast found for {show} {season_key}. Check the season key (e.g. US51, BB03).")

    wb = Workbook()
    how = wb.active
    how.title = "How to use"
    how["A1"], how["B1"] = "show", show
    how["A2"], how["B2"] = "season_key", season_key
    for i, line in enumerate(HOW_TO, start=4):
        how.cell(row=i, column=1, value=line)
    how["A4"].font = Font(bold=True, size=13)
    how.column_dimensions["A"].width = 110

    cs = wb.create_sheet("Cast")
    cs.append(["name", "full_name"])
    for name, full in cast:
        cs.append([name, full])
    style_header(cs, [("name", 22), ("full_name", 30)])
    names_ref = f"Cast!$A$2:$A${len(cast) + 1}"

    for title, cols in SHEETS.items():
        if title == "Showmances" and show != "bigbrother":
            continue
        ws = wb.create_sheet(title)
        ws.append([c for c, _ in cols])
        style_header(ws, cols)
        for idx, (col, _) in enumerate(cols, start=1):
            letter = ws.cell(row=1, column=idx).column_letter
            rng = f"{letter}2:{letter}{ROWS + 1}"
            if col in {"member", "planned_target", "voted_out", "ran_the_vote", "player_1", "player_2"}:
                dv = DataValidation(type="list", formula1=names_ref, allow_blank=True,
                                    error="Pick a name from the Cast tab.", showErrorMessage=True)
            elif col == "blindside":
                dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True)
            elif col.startswith("episode"):
                dv = DataValidation(type="whole", operator="between", formula1="1", formula2="30",
                                    allow_blank=True, error="Episode or week number (1-30).", showErrorMessage=True)
            else:
                continue
            ws.add_data_validation(dv)
            dv.add(rng)

    OUT.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    print(f"Created {path.relative_to(ROOT)} with {len(cast)} cast members.")


def style_header(ws, cols) -> None:
    for idx, (_, width) in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center")
        ws.column_dimensions[cell.column_letter].width = width
    ws.freeze_panes = "A2"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2].upper())
