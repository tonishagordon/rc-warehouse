"""
LOAD: parse the saved Big Brother HTML snapshots into DuckDB.

Wikipedia tables differ from season to season (merged cells, renamed
columns, special twists), so this script does NOT try to understand them.
It flattens every table into a generic "cell" format that never breaks:

    raw_bigbrother.wiki_tables  one row per table: season, section heading,
                                caption, size, column headers
    raw_bigbrother.wiki_cells   one row per cell: season, table, row, column,
                                column header, value

dbt staging models then pick out the tables they need (houseguests,
voting history...) and turn the cells into proper columns. This is the
"ELT" pattern: load first, transform in the warehouse.

Usage (from the repo root):
    python ingest/load_bigbrother.py
"""

import gzip
import json
from io import StringIO
from pathlib import Path

import duckdb
import pandas as pd
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
HTML_DIR = REPO_ROOT / "data" / "raw" / "bigbrother" / "html"
MANIFEST = REPO_ROOT / "data" / "raw" / "bigbrother" / "manifest.json"
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCHEMA = "raw_bigbrother"


def clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # pandas turns 29 into 29.0 when a column has blanks
    text = " ".join(str(value).split())
    return text or None


def flatten_header(col) -> str:
    """Multi-row headers come back as tuples; join the distinct parts."""
    parts = col if isinstance(col, tuple) else (col,)
    seen = []
    for p in parts:
        p = clean_text(p)
        if p and not p.startswith("Unnamed:") and p not in seen:
            seen.append(p)
    return " | ".join(seen) if seen else ""


def section_for(table) -> str | None:
    """Nearest heading above the table (e.g. 'Voting history')."""
    heading = table.find_previous(["h2", "h3", "h4"])
    return clean_text(heading.get_text(" ")) if heading else None


def strip_footnotes(soup: BeautifulSoup) -> None:
    """Remove [1]-style reference markers and hidden sort keys from cells."""
    for tag in soup.select("sup.reference, span.sortkey, style"):
        tag.decompose()
    for tag in soup.select("[style*='display:none']"):
        tag.decompose()


def parse_season(key: str, html: str, fetched_at: str | None):
    soup = BeautifulSoup(html, "lxml")
    strip_footnotes(soup)
    tables_out, cells_out = [], []

    for t_idx, table in enumerate(soup.select("table.wikitable")):
        caption = clean_text(table.caption.get_text(" ")) if table.caption else None
        section = section_for(table)
        try:
            df = pd.read_html(StringIO(str(table)), flavor="lxml")[0]
        except ValueError:
            continue  # table with no parsable rows

        headers = [flatten_header(c) for c in df.columns]
        tables_out.append({
            "season_key": key,
            "table_index": t_idx,
            "section": section,
            "caption": caption,
            "n_rows": len(df),
            "n_cols": len(headers),
            "headers": " || ".join(headers),
        })
        for r_idx, row in enumerate(df.itertuples(index=False)):
            for c_idx, value in enumerate(row):
                cells_out.append({
                    "season_key": key,
                    "table_index": t_idx,
                    "row_index": r_idx,
                    "col_index": c_idx,
                    "column_header": headers[c_idx],
                    "value": clean_text(value),
                    "_fetched_at": fetched_at,
                })
    return tables_out, cells_out


def main() -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    files = sorted(HTML_DIR.glob("BB*.html.gz"))
    if not files:
        raise SystemExit(f"No snapshots in {HTML_DIR}. Run scrape_bigbrother.py first.")

    all_tables, all_cells = [], []
    for path in files:
        key = path.name.split(".")[0]
        with gzip.open(path, "rt", encoding="utf-8") as f:
            html = f.read()
        tables, cells = parse_season(key, html, manifest.get(key, {}).get("fetched_at"))
        all_tables += tables
        all_cells += cells
        print(f"  {key}: {len(tables):>2} tables, {len(cells):>6,} cells")

    tables_df = pd.DataFrame(all_tables)
    cells_df = pd.DataFrame(all_cells)

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    for name, df in [("wiki_tables", tables_df), ("wiki_cells", cells_df)]:
        con.register("df_view", df)
        con.execute(f"CREATE OR REPLACE TABLE {SCHEMA}.{name} AS SELECT * FROM df_view")
        con.unregister("df_view")
    con.close()

    print(f"\nLoaded {len(tables_df):,} tables and {len(cells_df):,} cells into {SCHEMA}.")


if __name__ == "__main__":
    main()
