"""
Reality Competition Warehouse: explorer app.

Reads the Parquet exports of the dbt marts (data/marts/), so it runs anywhere
without the pipeline. Rebuild them with: bash scripts/build_warehouse.sh

Run locally (from the repo root):
    streamlit run app/streamlit_app.py
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "marts"
REPO_URL = "https://github.com/tonishagordon/rc-warehouse"
DOCS_URL = "https://tonishagordon.github.io/rc-warehouse/"

SHOW_TITLES = {
    "survivor": "Survivor",
    "bigbrother": "Big Brother",
    "challenge": "The Challenge",
    "traitors": "The Traitors",
}
SHOW_ORDER = list(SHOW_TITLES.values())

# Validated categorical slots (dataviz reference palette, light mode) + a
# neutral for "everything else". Identity is never color-alone: every chart
# has a legend or labeled axis, and a table view sits underneath.
BLUE, ORANGE, NEUTRAL = "#2a78d6", "#eb6834", "#a3a29d"

EXIT_LABELS = {
    "jury_vote": "Jury vote", "final_challenge": "Final challenge", "final_vote": "End game",
    "vote_out": "Voted out", "eviction": "Evicted", "banished": "Banished", "murdered": "Murdered",
    "elimination_round": "Elimination", "quit": "Quit / walked", "removed": "Removed",
    "medical": "Medical",
}

st.set_page_config(page_title="Reality Competition Warehouse", layout="wide")


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    person = pd.read_parquet(DATA_DIR / "dim_person.parquet")
    season = pd.read_parquet(DATA_DIR / "dim_season.parquet")
    appearance = pd.read_parquet(DATA_DIR / "fct_appearance.parquet")
    appearance["show_title"] = appearance["show_name"].map(SHOW_TITLES)
    appearance["premiered_date"] = pd.to_datetime(appearance["premiered_date"])
    appearance["how_they_left"] = appearance["exit_method"].map(EXIT_LABELS)
    appearance["outcome"] = appearance.apply(
        lambda r: "Won" if r["is_winner"] else ("Made the final" if r["made_final"] else "Out before the final"),
        axis=1,
    )
    return person, season, appearance


if not (DATA_DIR / "fct_appearance.parquet").exists():
    st.error("No data found in data/marts/. Run `bash scripts/build_warehouse.sh` first.")
    st.stop()

person, season, appearance = load()

# ---------------------------------------------------------------- header
st.title("Reality Competition Warehouse")
st.caption(
    "Survivor · Big Brother · The Challenge · The Traitors, resolved to one person per contestant. "
    f"[Code on GitHub]({REPO_URL}) · [dbt docs + lineage]({DOCS_URL})"
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("People", f"{len(person):,}")
k2.metric("Season appearances", f"{len(appearance):,}")
k3.metric("Seasons", f"{len(season):,}")
k4.metric("Cross-show careers", f"{int(person['is_crossover'].sum()):,}")

tab_career, tab_feeder, tab_traitors, tab_about = st.tabs(
    ["Career Explorer", "Feeder Show Report", "The Strategist Penalty", "About the data"]
)

# ---------------------------------------------------------------- career explorer
with tab_career:
    st.subheader("Career Explorer")
    st.write("Pick anyone to see every season they played, in order, across all four shows.")

    choices = person.sort_values(["n_appearances", "person_name"], ascending=[False, True]).copy()
    choices["label"] = choices["person_name"] + "  ·  " + choices["n_appearances"].astype(str) + " seasons"
    labels = choices["label"].tolist()
    default = next((i for i, n in enumerate(choices["person_name"]) if n == "Cirie Fields"), 0)

    c1, c2 = st.columns([3, 1])
    crossover_only = c2.toggle("Cross-show careers only", value=False)
    if crossover_only:
        choices = choices[choices["is_crossover"]]
        labels = choices["label"].tolist()
        default = next((i for i, n in enumerate(choices["person_name"]) if n == "Cirie Fields"), 0)
    picked = c1.selectbox("Contestant", labels, index=default)
    pid = choices.loc[choices["label"] == picked, "person_id"].iloc[0]
    p = person.loc[person["person_id"] == pid].iloc[0]
    career = appearance[appearance["person_id"] == pid].sort_values("premiered_date")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Seasons played", len(career))
    m2.metric("Shows", int(p["n_shows"]))
    m3.metric("Wins", int(career["is_winner"].sum()))
    m4.metric("Finals reached", int(career["made_final"].sum()))
    if p["name_variants"] and " | " in p["name_variants"]:
        st.caption(f"Also billed as: {p['name_variants']}")

    shows_present = [sh for sh in SHOW_ORDER if sh in set(career["show_title"])]
    timeline = (
        alt.Chart(career)
        .mark_circle(size=220, opacity=1, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("premiered_date:T", title="Season premiere",
                    axis=alt.Axis(format="%Y", tickCount="year", grid=False)),
            # one row per show the person actually played, in a fixed order
            y=alt.Y("show_title:N", title=None, scale=alt.Scale(domain=shows_present),
                    axis=alt.Axis(labelLimit=0)),
            color=alt.Color(
                "outcome:N",
                title="Result",
                scale=alt.Scale(
                    domain=["Won", "Made the final", "Out before the final"],
                    range=[ORANGE, BLUE, NEUTRAL],
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("season_name:N", title="Season"),
                alt.Tooltip("premiered_year:Q", title="Year", format="d"),
                alt.Tooltip("outcome:N", title="Result"),
                alt.Tooltip("finish_place:Q", title="Place"),
                alt.Tooltip("cast_size:Q", title="Cast size"),
                alt.Tooltip("finish_percentile:Q", title="Finish percentile", format=".2f"),
                alt.Tooltip("name_as_billed:N", title="Billed as"),
            ],
        )
        .properties(height=alt.Step(56))
    )
    st.altair_chart(timeline, width="stretch")

    st.dataframe(
        career[["premiered_year", "show_title", "season_name", "outcome", "how_they_left", "finish_place",
                "cast_size", "finish_percentile", "game_role", "name_as_billed"]]
        .rename(columns={
            "premiered_year": "Year", "show_title": "Show", "season_name": "Season",
            "outcome": "Result", "how_they_left": "How it ended", "finish_place": "Place", "cast_size": "Cast",
            "finish_percentile": "Finish percentile", "game_role": "Traitors role",
            "name_as_billed": "Billed as",
        }),
        hide_index=True, width="stretch",
    )
    st.caption("Finish percentile: 1.0 = won, 0.0 = first out, so seasons of different sizes compare fairly.")

# ---------------------------------------------------------------- feeder show report
with tab_feeder:
    st.subheader("Feeder Show Report")
    st.write(
        "How do players do in their **first** season of The Challenge, depending on where they "
        "first became known?"
    )
    min_n = st.slider("Only show backgrounds with at least this many players", 3, 30, 8)

    first_ch = appearance[(appearance["show_name"] == "challenge") & (appearance["show_appearance_number"] == 1)]
    first_ch = first_ch.merge(person[["person_id", "background"]], on="person_id")
    first_ch = first_ch[first_ch["background"].notna() & (first_ch["background"] != "Unknown")]
    feeder = (
        first_ch.groupby("background")
        .agg(players=("person_id", "count"),
             avg_finish_percentile=("finish_percentile", "mean"),
             made_final_rate=("made_final", "mean"),
             wins=("is_winner", "sum"))
        .reset_index()
    )
    feeder = feeder[feeder["players"] >= min_n].sort_values("avg_finish_percentile", ascending=False)

    bars = (
        alt.Chart(feeder)
        .mark_bar(color=BLUE, cornerRadiusEnd=4, height={"band": 0.7})
        .encode(
            x=alt.X("avg_finish_percentile:Q", title="Average finish percentile in first Challenge",
                    scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("background:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("background:N", title="Background"),
                alt.Tooltip("players:Q", title="Players"),
                alt.Tooltip("avg_finish_percentile:Q", title="Avg finish percentile", format=".2f"),
                alt.Tooltip("made_final_rate:Q", title="Made the final", format=".0%"),
                alt.Tooltip("wins:Q", title="Wins"),
            ],
        )
        .properties(height=40 * max(len(feeder), 1) + 40)
    )
    midline = alt.Chart(pd.DataFrame({"x": [0.5]})).mark_rule(color=NEUTRAL, strokeDash=[4, 4]).encode(x="x:Q")
    st.altair_chart(bars + midline, width="stretch")

    st.dataframe(
        feeder.rename(columns={
            "background": "Background", "players": "Players",
            "avg_finish_percentile": "Avg finish percentile",
            "made_final_rate": "Made the final", "wins": "Wins",
        }).style.format({"Avg finish percentile": "{:.2f}", "Made the final": "{:.0%}"}),
        hide_index=True, width="stretch",
    )
    st.caption(
        "Background = Survivor or Big Brother if the player debuted there; otherwise the origin show "
        "their first Challenge cast table lists. Dashed line = middle of the pack. Small groups are "
        "noisy: use the slider to hide them."
    )

# ---------------------------------------------------------------- strategist penalty
with tab_traitors:
    st.subheader("The Strategist Penalty")
    st.write(
        "On The Traitors, are Survivor and Big Brother alums, people known for strategy, "
        "treated differently from everyone else?"
    )
    tr = appearance[appearance["show_name"] == "traitors"].merge(
        person[["person_id", "person_name", "survivor_seasons", "bigbrother_seasons"]], on="person_id"
    )
    tr["group"] = (tr["survivor_seasons"] + tr["bigbrother_seasons"] > 0).map(
        {True: "Survivor / Big Brother alums", False: "Everyone else"}
    )
    rates = (
        tr.assign(
            traitor=tr["game_role"].eq("Traitor"),
            banished=tr["exit_method"].eq("banished"),
            murdered=tr["exit_method"].eq("murdered"),
        )
        .groupby("group")
        .agg(players=("person_id", "count"),
             **{"Cast as a Traitor": ("traitor", "mean"),
                "Banished": ("banished", "mean"),
                "Murdered": ("murdered", "mean"),
                "Made the final": ("made_final", "mean")},
             wins=("is_winner", "sum"),
             avg_finish=("finish_percentile", "mean"))
        .reset_index()
    )
    long = rates.melt(id_vars=["group", "players"],
                      value_vars=["Cast as a Traitor", "Banished", "Murdered", "Made the final"],
                      var_name="measure", value_name="rate")

    groups = ["Survivor / Big Brother alums", "Everyone else"]
    grouped = (
        alt.Chart(long)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("measure:N", title=None,
                    sort=["Cast as a Traitor", "Banished", "Murdered", "Made the final"],
                    axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("group:N", sort=groups),
            y=alt.Y("rate:Q", title="Share of players", axis=alt.Axis(format="%")),
            color=alt.Color("group:N", title=None, sort=groups,
                            scale=alt.Scale(domain=groups, range=[ORANGE, BLUE]),
                            legend=alt.Legend(orient="top", labelLimit=0)),
            tooltip=[alt.Tooltip("group:N", title="Group"),
                     alt.Tooltip("measure:N", title="Measure"),
                     alt.Tooltip("rate:Q", title="Share", format=".0%"),
                     alt.Tooltip("players:Q", title="Players in group")],
        )
        .properties(height=340)
    )
    st.altair_chart(grouped, width="stretch")

    st.dataframe(
        rates.rename(columns={"group": "Group", "players": "Players", "wins": "Wins",
                              "avg_finish": "Avg finish percentile"})
        .style.format({c: "{:.0%}" for c in ["Cast as a Traitor", "Banished", "Murdered", "Made the final"]}
                      | {"Avg finish percentile": "{:.2f}"}),
        hide_index=True, width="stretch",
    )

    with st.expander("The alums, season by season"):
        alums = tr[tr["group"] == "Survivor / Big Brother alums"].sort_values(["season_key", "finish_place"])
        st.dataframe(
            alums[["season_name", "person_name", "origin_listed", "game_role", "outcome", "how_they_left", "finish_place"]]
            .rename(columns={"season_name": "Season", "person_name": "Player", "origin_listed": "Known from",
                             "game_role": "Role", "outcome": "Result", "how_they_left": "How they left",
                             "finish_place": "Place"}),
            hide_index=True, width="stretch",
        )
    st.caption(
        f"{int(rates['players'].sum())} Traitors appearances across {tr['season_key'].nunique()} seasons. "
        "The samples are small, so read these as patterns worth watching, not proof."
    )

# ---------------------------------------------------------------- about
with tab_about:
    st.subheader("About the data")
    st.markdown(
        f"""
This app sits on top of a **DuckDB + dbt warehouse** that combines four sources:

- **Survivor:** the [survivoR](https://github.com/doehm/survivoR) dataset by Daniel Oehm (MIT)
- **Big Brother, The Challenge, The Traitors:** Wikipedia season pages (CC BY-SA 4.0), saved as snapshots

The hard part is **entity resolution**: working out that *"John Devenanzio"*, *"Johnny Devenanzio"*
and *Johnny "Bananas" Devenanzio* are one person, or that a Challenge player listed as
"Big Brother 20" is the Fessy from Big Brother 20. It uses name normalization, blocking on the
season a player came from, similarity scoring, graph clustering, and a hand-checked crosswalk.

Every push to GitHub rebuilds the warehouse and runs 100+ automated data tests.

- [Code, README and design decisions]({REPO_URL})
- [dbt docs: every model, column and the lineage graph]({DOCS_URL})
"""
    )
    shows = (
        season.groupby("show_name")
        .agg(seasons=("season_key", "count"), first=("premiered_year", "min"), last=("premiered_year", "max"))
        .reset_index()
    )
    shows["show_name"] = shows["show_name"].map(SHOW_TITLES)
    st.dataframe(shows.rename(columns={"show_name": "Show", "seasons": "Seasons",
                                       "first": "First season", "last": "Latest season"}),
                 hide_index=True)
