"""Shared design tokens, CSS, helpers and data loading for every page."""

import json
import textwrap
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "marts"
REPO_URL = "https://github.com/tonishagordon/rc-warehouse"
DOCS_URL = "https://tonishagordon.github.io/rc-warehouse/"

# ------------------------------------------------------------------ design tokens
# Dark chart palette (validated: categorical slots 1-4 pass lightness, chroma,
# CVD and contrast checks on the #1a1a19 surface).
SURFACE = "#1a1a19"
INK, INK_2, INK_3 = "#f0efec", "#c3c2b7", "#8a8983"
GRID = "#2e2e2b"
BLUE, ORANGE, AQUA, AMBER = "#3987e5", "#d95926", "#199e70", "#c98500"
SERIF = "'Source Serif 4', Georgia, serif"
SANS = "'Inter', system-ui, sans-serif"

SHOW_TITLES = {"survivor": "Survivor", "bigbrother": "Big Brother",
               "challenge": "The Challenge", "traitors": "The Traitors"}
SHOW_ORDER = list(SHOW_TITLES.values())
EXIT_LABELS = {
    "jury_vote": "Jury vote", "final_challenge": "Final challenge", "final_vote": "End game",
    "vote_out": "Voted out", "eviction": "Evicted", "banished": "Banished", "murdered": "Murdered",
    "elimination_round": "Elimination", "quit": "Quit / walked", "removed": "Removed",
    "medical": "Medical", "idoled_out": "Idoled out", "fire_making": "Lost fire-making",
}


def inject_css() -> None:
    st.markdown(textwrap.dedent(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

    html, body, [data-testid="stAppViewContainer"] {{ background: {SURFACE}; }}
    [data-testid="stMainBlockContainer"] {{ max-width: 820px; padding-top: 3rem; }}
    [data-testid="stHeader"] {{ background: {SURFACE}; border-bottom: 1px solid {GRID}; }}
    html, body, p, li, label, [data-testid="stMarkdownContainer"] {{ font-family: {SANS}; }}
    [data-testid="stMarkdownContainer"] p {{ color: {INK_2}; font-size: 1.05rem; line-height: 1.7; }}

    .kicker {{ font: 600 0.75rem/1 {SANS}; letter-spacing: .16em; text-transform: uppercase;
               color: {ORANGE}; margin: 0 0 .9rem; }}
    .hero-title {{ font: 700 3.6rem/1.02 {SERIF}; color: {INK}; margin: 0 0 1rem; letter-spacing: -.01em; }}
    .deck {{ font: 400 1.3rem/1.5 {SERIF}; color: {INK_2}; margin: 0 0 1.4rem; }}
    .byline {{ font: 500 .8rem/1.4 {SANS}; color: {INK_3}; letter-spacing: .04em;
               border-top: 1px solid {GRID}; padding-top: .9rem; margin-bottom: 2.4rem; }}
    .byline a {{ color: {INK_2}; }}
    .stats {{ display: flex; gap: 2.5rem; flex-wrap: wrap; margin: 0 0 3.5rem; }}
    .stat-num {{ font: 600 2.6rem/1 {SERIF}; color: {INK}; }}
    .stat-label {{ font: 500 .8rem/1.3 {SANS}; color: {INK_3}; margin-top: .4rem; max-width: 11rem; }}

    .chapter {{ border-top: 1px solid {GRID}; margin-top: 4.5rem; padding-top: 2.2rem; }}
    .ch-num {{ font: 600 .75rem/1 {SANS}; letter-spacing: .16em; text-transform: uppercase; color: {INK_3}; }}
    .ch-title {{ font: 700 2.2rem/1.1 {SERIF}; color: {INK}; margin: .6rem 0 1.2rem; }}
    .pull {{ display: flex; gap: 1.2rem; align-items: baseline; margin: 1.4rem 0 1.6rem; }}
    .pull-num {{ font: 700 3.2rem/1 {SERIF}; color: {ORANGE}; white-space: nowrap; }}
    .pull-text {{ font: 400 1.1rem/1.45 {SERIF}; color: {INK}; }}
    .note {{ font: 400 .82rem/1.55 {SANS}; color: {INK_3}; border-left: 2px solid {GRID};
             padding-left: .9rem; margin: .8rem 0 0; }}
    .sidebar {{ background: #242422; border-radius: 6px; padding: 1.4rem 1.6rem; margin: 3.5rem 0 0; }}
    .sidebar h4 {{ font: 600 .75rem/1 {SANS}; letter-spacing: .16em; text-transform: uppercase;
                   color: {ORANGE}; margin: 0 0 1rem; }}
    .sidebar .fact {{ font: 400 1.02rem/1.5 {SERIF}; color: {INK}; margin: 0 0 .8rem; }}
    .sidebar .fact b {{ font-weight: 700; }}
    .footer {{ border-top: 1px solid {GRID}; margin-top: 4rem; padding-top: 1.4rem;
               font: 400 .85rem/1.6 {SANS}; color: {INK_3}; }}
    .footer a {{ color: {INK_2}; }}
    [data-testid="stDataFrame"] {{ margin-top: .5rem; }}
    .subhead {{ font: 700 1.45rem/1.25 {SERIF}; color: {INK}; margin: 3rem 0 .4rem; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 1rem; margin: 1rem 0 1.2rem; }}
    .card {{ background: #242422; border-radius: 6px; padding: 1.1rem 1.2rem; border-top: 3px solid {ORANGE}; }}
    .card-name {{ font: 700 1.2rem/1.2 {SERIF}; color: {INK}; }}
    .card-meta {{ font: 400 .8rem/1.45 {SANS}; color: {INK_3}; margin-top: .3rem; }}
    .card-stats {{ display: flex; gap: 1rem; font: 400 .85rem/1.4 {SANS}; color: {INK_2}; margin-top: .7rem; }}
    .card-stats b {{ font: 600 1.1rem/1 {SERIF}; color: {INK}; }}
    .card-odds {{ font: 400 .9rem/1.4 {SANS}; color: {INK_2}; margin-top: .7rem; border-top: 1px solid {GRID}; padding-top: .6rem; }}
    .card-odds b {{ color: {ORANGE}; font-weight: 600; }}
    .card-odds span {{ color: {INK_3}; }}
    .next-page {{ font: 400 1.05rem/1.55 {SERIF}; color: {INK_2}; border-top: 1px solid {GRID};
                  margin-top: 4rem; padding-top: 1.6rem; }}
    .next-page b {{ color: {INK}; }}
    [data-testid="stPageLink"] p {{ color: {ORANGE} !important; font-weight: 600; font-family: {SANS}; }}
    [data-baseweb="tab"] p {{ font: 600 .95rem/1 {SANS}; }}
    [data-baseweb="tab-list"] {{ margin: 1rem 0 .5rem; }}
    [data-testid="stHeader"] a, [data-testid="stHeader"] a p, [data-testid="stHeader"] a span {{
        font-size: .8rem !important; font-family: {SANS} !important; letter-spacing: .03em; }}
    [data-testid="stHeader"] a {{ padding: .2rem .55rem !important; min-height: 0 !important; }}
    </style>
    """), unsafe_allow_html=True)



def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def chapter(num: str, title: str) -> None:
    html(f'<div class="chapter"><div class="ch-num">{num}</div><div class="ch-title">{title}</div></div>')


def pull(number: str, text: str) -> None:
    html(f'<div class="pull"><div class="pull-num">{number}</div><div class="pull-text">{text}</div></div>')


def note(text: str) -> None:
    html(f'<p class="note">{text}</p>')


def themed(chart: alt.Chart) -> alt.Chart:
    """Dark editorial chart styling: no background, recessive axes and grid."""
    return (
        chart.configure(background="transparent", font="Inter")
        .configure_view(stroke=None)
        .configure_axis(labelColor=INK_2, titleColor=INK_3, gridColor=GRID, domainColor=GRID,
                        tickColor=GRID, labelFontSize=12, titleFontSize=12, titleFontWeight=500,
                        labelFont="Inter", titleFont="Inter")
        .configure_legend(labelColor=INK_2, titleColor=INK_3, labelFontSize=12, titleFontSize=12,
                          orient="top", symbolType="circle", labelLimit=0)
    )


def pct(x: float) -> str:
    return f"{x:.0%}"


# ------------------------------------------------------------------ data
@st.cache_data
def load():
    person = pd.read_parquet(DATA_DIR / "dim_person.parquet")
    season = pd.read_parquet(DATA_DIR / "dim_season.parquet")
    app = pd.read_parquet(DATA_DIR / "fct_appearance.parquet")
    app["premiered_date"] = pd.to_datetime(app["premiered_date"])
    app["show_title"] = app["show_name"].map(SHOW_TITLES)
    app["how_it_ended"] = app["exit_method"].map(EXIT_LABELS)
    app["outcome"] = app.apply(
        lambda r: "Won" if r["is_winner"] else ("Made the final" if r["made_final"] else "Out before the final"),
        axis=1)
    app = app.merge(person[["person_id", "person_name", "background", "challenge_seasons",
                            "survivor_seasons", "bigbrother_seasons"]], on="person_id")
    return person, season, app



def footer(extra: str = "") -> None:
    html(f"""
<div class="footer">
<b>Methods.</b> Survivor data from the <a href="https://github.com/doehm/survivoR">survivoR</a> dataset (MIT);
Big Brother, The Challenge and The Traitors from Wikipedia season pages (CC BY-SA 4.0). US seasons only.
Each appearance was matched to one person with name normalization, blocking on the season a player
came from, similarity scoring, graph clustering and a hand-checked crosswalk. "Finish" is the share of
the cast a player outlasted, so seasons of different sizes compare fairly. The warehouse is rebuilt and tested on every change.{extra}
<br><br><a href="{REPO_URL}">Code, README and design decisions</a> &nbsp;·&nbsp;
<a href="{DOCS_URL}">dbt docs and lineage</a>
</div>
""")
