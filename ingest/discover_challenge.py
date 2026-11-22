"""
DISCOVER: build the list of Challenge seasons to scrape.

Challenge season pages have names, not numbers ("Real World/Road Rules
Challenge: The Gauntlet", "The Challenge: Battle of the Eras"...), so we
read the season tables on the main "The Challenge (TV series)" article and
collect each season's page link.

Output: data/raw/challenge/season_index.csv, a small file you can open and
edit. Set include=N to skip a row, or add rows by hand (e.g. a spin-off the
main article doesn't link). scrape_challenge.py reads this file.
International versions are listed with include=N (US scope).

Usage (from the repo root):
    python ingest/discover_challenge.py
"""

import csv
import re
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

from scrape_bigbrother import fetch  # same Wikipedia API helper

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_CSV = REPO_ROOT / "data" / "raw" / "challenge" / "season_index.csv"
MAIN_ARTICLE = "The Challenge (TV series)"
NON_ARTICLE_NAMESPACES = ("File:", "Help:", "Template:", "Category:", "Wikipedia:", "Special:")

# Seasons the main article doesn't link from its tables. Added on every run,
# so they survive re-running discovery.
MANUAL_SEASONS = [
    {"season_key": "CUSA02", "series": "The Challenge: USA", "order": 2,
     "title": "The Challenge: USA season 2", "page_title": "The Challenge: USA season 2", "include": "Y"},
]

INTERNATIONAL = ("australia", "argentina", "desafío", "desafio", "challenge uk", "sverige", "brasil", "españa", "mexico")


def clean(text: str) -> str:
    return " ".join(text.split())


def key_for(page: str, order_num: int) -> tuple[str, str]:
    """Season key + include flag, decided from the page title.

    Main MTV seasons use the series order (CH01...). Spin-offs use their own
    prefix plus the season number in the page title. International versions
    are listed but excluded (US scope, see docs/decisions.md D001).
    """
    p = page.lower()
    m = re.search(r"season (\d+)", p)
    n = int(m.group(1)) if m else 1
    if any(word in p for word in INTERNATIONAL):
        return f"CINT{order_num:02d}", "N"
    if "usa" in p:
        return f"CUSA{n:02d}", "Y"
    if "challenge: all stars" in p:  # not "Road Rules: All Stars" (season 1)
        return f"CAS{n:02d}", "Y"
    if "champs vs. pros" in p:
        return "CVP01", "Y"
    if "champs vs. stars" in p:
        return f"CVS{n:02d}", "Y"
    if "world championship" in p:
        return f"CWC{n:02d}", "Y"
    if "list of" in p:
        return f"SKIP{order_num:02d}", "N"
    return f"CH{order_num:02d}", "Y"


def link_target(cell) -> str | None:
    """First link in a cell that points to another article (not an anchor or file)."""
    for a in cell.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/wiki/"):
            continue
        target = unquote(href.split("/wiki/", 1)[1]).split("#")[0].replace("_", " ")
        if target and not target.startswith(NON_ARTICLE_NAMESPACES) and target != MAIN_ARTICLE:
            return target
    return None


def discover(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("sup.reference"):
        tag.decompose()
    rows_out, seen = [], set()

    for table in soup.select("table.wikitable"):
        header_cells = table.find("tr").find_all(["th", "td"])
        headers = [clean(h.get_text(" ")).lower() for h in header_cells]
        # Prefer the Title column; the Season-number column links to episode lists.
        title_idx = next((i for i, h in enumerate(headers) if h.startswith("title")), None)
        if title_idx is None:
            title_idx = next((i for i, h in enumerate(headers) if h == "season"), None)
        if title_idx is None:
            continue
        order_idx = next((i for i, h in enumerate(headers)
                          if i != title_idx and h in ("order", "no.", "#", "season", "season no.")), None)

        heading = table.find_previous(["h2", "h3", "h4"])
        section = clean(heading.get_text(" ")) if heading else None

        for n, tr in enumerate(table.find_all("tr")[1:], start=1):
            cells = tr.find_all(["th", "td"])
            if len(cells) <= title_idx:
                continue
            title_cell = cells[title_idx]
            page = link_target(title_cell)
            if not page or page in seen:
                continue
            order_text = clean(cells[order_idx].get_text(" ")) if order_idx is not None and len(cells) > order_idx else ""
            order_num = int(m.group(1)) if (m := re.search(r"(\d+)", order_text)) else n
            seen.add(page)
            key, include = key_for(page, order_num)
            rows_out.append({
                "season_key": key,
                "series": section or "",
                "order": order_num,
                "title": clean(title_cell.get_text(" ")),
                "page_title": page,
                "include": include,
            })
    return rows_out


def main() -> None:
    parsed = fetch(MAIN_ARTICLE)
    rows = discover(parsed["text"])
    found = {r["page_title"] for r in rows}
    rows += [dict(m) for m in MANUAL_SEASONS if m["page_title"] not in found]

    # make keys unique if two tables share a prefix
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["season_key"]] = counts.get(r["season_key"], 0) + 1
        if counts[r["season_key"]] > 1:
            r["season_key"] += chr(ord("a") + counts[r["season_key"]] - 2)

    INDEX_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Found {len(rows)} season pages -> {INDEX_CSV.relative_to(REPO_ROOT)}\n")
    for r in rows:
        flag = "" if r["include"] == "Y" else "   (excluded)"
        print(f"  {r['season_key']:<7} {r['title'][:50]:<50} -> {r['page_title']}{flag}")


if __name__ == "__main__":
    main()
