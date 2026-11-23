"""Look anyone up: one player's whole career across all four shows."""

import altair as alt
import pandas as pd
import streamlit as st

from common import BLUE, DATA_DIR, INK_3, ORANGE, SHOW_ORDER, SURFACE, footer, html, load, note, themed

person, season, app = load()

html(f"""
<div class="kicker">Player lookup · {len(person):,} careers</div>
<div class="hero-title">Look Anyone Up</div>
<div class="deck">Every season, every show. Pick a player to see their whole career in order.</div>
""")


@st.cache_data
def load_moves():
    sv_path, bb_path = DATA_DIR / "mart_survivor_moves.parquet", DATA_DIR / "mart_bigbrother_moves.parquet"
    if not (sv_path.exists() and bb_path.exists()):
        return None, None
    return pd.read_parquet(sv_path), pd.read_parquet(bb_path)


sv, bb = load_moves()
choices = person.sort_values(["n_appearances", "person_name"], ascending=[False, True]).copy()
crossover_only = st.toggle("Only players who crossed between shows", value=True)
if crossover_only:
    choices = choices[choices["is_crossover"]]
choices["label"] = choices["person_name"] + "  ·  " + choices["n_appearances"].astype(str) + " seasons"
labels_list = choices["label"].tolist()
default = next((i for i, n in enumerate(choices["person_name"]) if n == "Cirie Fields"), 0)
picked = st.selectbox("Player", labels_list, index=default, label_visibility="collapsed")
pid = choices.loc[choices["label"] == picked, "person_id"].iloc[0]
p = person.loc[person["person_id"] == pid].iloc[0]
career = app[app["person_id"] == pid].sort_values("premiered_date")

html(f"""
<div class="stats" style="margin:1.2rem 0 1rem">
  <div><div class="stat-num">{len(career)}</div><div class="stat-label">seasons</div></div>
  <div><div class="stat-num">{int(p['n_shows'])}</div><div class="stat-label">shows</div></div>
  <div><div class="stat-num">{int(career['is_winner'].sum())}</div><div class="stat-label">wins</div></div>
  <div><div class="stat-num">{int(career['made_final'].sum())}</div><div class="stat-label">finals</div></div>
</div>
""")
shows_present = [s for s in SHOW_ORDER if s in set(career["show_title"])]
timeline = (
    alt.Chart(career)
    .mark_circle(size=230, opacity=1, stroke=SURFACE, strokeWidth=2)
    .encode(
        x=alt.X("premiered_date:T", title=None, axis=alt.Axis(format="%Y", tickCount="year", grid=False)),
        y=alt.Y("show_title:N", title=None, scale=alt.Scale(domain=shows_present),
                axis=alt.Axis(labelLimit=0, domain=False, ticks=False)),
        color=alt.Color("outcome:N", title=None,
                        scale=alt.Scale(domain=["Won", "Made the final", "Out before the final"],
                                        range=[ORANGE, BLUE, INK_3])),
        tooltip=[alt.Tooltip("season_name:N", title="Season"),
                 alt.Tooltip("premiered_year:Q", title="Year", format="d"),
                 alt.Tooltip("outcome:N", title="Result"), alt.Tooltip("how_it_ended:N", title="How it ended"),
                 alt.Tooltip("finish_place:Q", title="Place"), alt.Tooltip("cast_size:Q", title="Cast size"),
                 alt.Tooltip("name_as_billed:N", title="Billed as")],
    )
    .properties(height=alt.Step(56))
)
st.altair_chart(themed(timeline), width="stretch")
st.dataframe(
    career[["premiered_year", "show_title", "season_name", "outcome", "how_it_ended", "finish_place",
            "cast_size", "game_role"]]
    .rename(columns={"premiered_year": "Year", "show_title": "Show", "season_name": "Season",
                     "outcome": "Result", "how_it_ended": "How it ended", "finish_place": "Place",
                     "cast_size": "Cast", "game_role": "Traitors role"}),
    hide_index=True, width="stretch")
def n(x) -> str:
    """Whole number for a stat tile, or a dash when the season hasn't finished."""
    return "–" if pd.isna(x) else f"{int(x)}"


def stat_table(df: pd.DataFrame, cols: dict, title: str, totals: list[tuple[str, str]]) -> None:
    html(f'<div class="subhead">{title}</div>')
    html('<div class="stats" style="margin:.8rem 0 1rem">' + "".join(
        f'<div><div class="stat-num">{v}</div><div class="stat-label">{lab}</div></div>' for v, lab in totals)
        + "</div>")
    st.dataframe(df[list(cols)].rename(columns=cols), hide_index=True, width="stretch")


if sv is not None:
    mine = sv[sv["person_id"] == pid].sort_values("season_key")
    if len(mine):
        stat_table(
            mine.assign(days=mine["days_lasted"].astype("Int64")),
            {"season_name": "Season", "days": "Days lasted", "individual_immunity_wins": "Immunity wins",
             "individual_reward_wins": "Reward wins", "votes_against": "Votes against them",
             "idols_found": "Idols found", "idol_plays": "Idols played"},
            "On Survivor",
            [(n(mine["days_lasted"].sum(min_count=1)), "days played"),
             (f"{int(mine['individual_immunity_wins'].sum())}", "individual immunity wins"),
             (f"{int(mine['idols_found'].sum())}", "idols found"),
             (f"{int(mine['votes_against'].sum())}", "votes cast against them")])
        note("Days lasted is blank for a season still airing. Votes against includes votes later cancelled by an idol.")
    mine_bb = bb[bb["person_id"] == pid].sort_values("season_key")
    if len(mine_bb):
        stat_table(
            mine_bb,
            {"season_name": "Season", "hoh_wins": "HOH wins", "veto_wins": "Veto wins",
             "weeks_nominated": "Weeks nominated"},
            "In the Big Brother house",
            [(f"{int(mine_bb['hoh_wins'].sum())}", "Head of Household wins"),
             (f"{int(mine_bb['veto_wins'].sum())}", "Power of Veto wins"),
             (f"{int(mine_bb['weeks_nominated'].sum())}", "weeks nominated for eviction")])

if p["name_variants"] and " | " in p["name_variants"]:
    note(f"Billed under different names over the years: {p['name_variants']}.")

footer()
