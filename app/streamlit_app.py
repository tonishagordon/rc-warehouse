"""
One Cast, Four Shows: a data story built on the Reality Competition Warehouse.

A single scrolling, dark editorial feature: five findings, each with a big
number, one chart and a short read, then a "look anyone up" explorer.

Reads the Parquet exports of the dbt marts (data/marts/), so it runs anywhere
without the pipeline. Rebuild them with: bash scripts/build_warehouse.sh
Run locally (from the repo root): streamlit run app/streamlit_app.py
"""

import json
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
    "medical": "Medical",
}

st.set_page_config(page_title="One Cast, Four Shows", layout="centered")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {{ background: {SURFACE}; }}
[data-testid="stMainBlockContainer"] {{ max-width: 820px; padding-top: 3rem; }}
[data-testid="stHeader"] {{ background: transparent; }}
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
</style>
""", unsafe_allow_html=True)


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


if not (DATA_DIR / "fct_appearance.parquet").exists():
    st.error("No data found in data/marts/. Run `bash scripts/build_warehouse.sh` first.")
    st.stop()

person, season, app = load()
challenge = app[app["show_name"] == "challenge"]

# ------------------------------------------------------------------ hero
html(f"""
<div class="kicker">A data story · Reality competition TV, 1998–2026</div>
<div class="hero-title">One Cast,<br>Four Shows</div>
<div class="deck">Survivor, Big Brother, The Challenge and The Traitors keep recasting each
other's players. Linking {len(app):,} season appearances into one record per person
shows who gets invited back, who travels well, and who gets punished for their reputation.</div>
<div class="byline">By Tonisha Gordon &nbsp;·&nbsp; Data: survivoR, Wikipedia &nbsp;·&nbsp;
<a href="{REPO_URL}">How it was built</a></div>
<div class="stats">
  <div><div class="stat-num">{len(person):,}</div><div class="stat-label">people, each resolved to one record</div></div>
  <div><div class="stat-num">{len(season)}</div><div class="stat-label">seasons across four shows</div></div>
  <div><div class="stat-num">{int(person['is_crossover'].sum())}</div><div class="stat-label">players who crossed between shows</div></div>
</div>
""")

# ------------------------------------------------------------------ 1. casting shift
def era(y: int) -> str:
    if y < 2005: return "1998–2004"
    if y < 2011: return "2005–2010"
    if y < 2017: return "2011–2016"
    if y < 2022: return "2017–2021"
    return "2022–2026"


def source(bg: str) -> str:
    if bg in ("The Real World", "Road Rules", "The Challenge"):
        return "MTV's own shows"
    if bg in ("Survivor", "Big Brother"):
        return "Survivor & Big Brother"
    if bg in ("Are You the One?", "Love Island", "Ex on the Beach", "Too Hot to Handle"):
        return "Dating shows"
    return "Everywhere else"


cast = challenge.assign(era=challenge["premiered_year"].astype(int).map(era),
                        source=challenge["background"].fillna("Unknown").map(source))
mix = cast.groupby(["era", "source"]).size().rename("n").reset_index()
mix["share"] = mix["n"] / mix.groupby("era")["n"].transform("sum")
early = mix[(mix["era"] == "2005–2010") & (mix["source"] == "MTV's own shows")]["share"].sum()
late = mix[(mix["era"] == "2022–2026") & (mix["source"] == "MTV's own shows")]["share"].sum()
sbb_late = mix[(mix["era"] == "2022–2026") & (mix["source"] == "Survivor & Big Brother")]["share"].sum()

chapter("Chapter 1", "MTV stopped casting only its own")
st.markdown(
    "For its first decade, The Challenge was a family reunion: every player came from MTV's "
    "*Real World* and *Road Rules*. Then the doors opened, first to dating shows, then to "
    "CBS's strategists.")
pull(f"{pct(early)} → {pct(late)}",
     f"MTV's own alumni went from {pct(early)} of Challenge casts (2005–2010) to {pct(late)} today. "
     f"Survivor and Big Brother players now fill {pct(sbb_late)}.")
sources = ["MTV's own shows", "Survivor & Big Brother", "Dating shows", "Everywhere else"]
eras = ["1998–2004", "2005–2010", "2011–2016", "2017–2021", "2022–2026"]
stack = (
    alt.Chart(mix)
    .mark_bar(stroke=SURFACE, strokeWidth=2, height={"band": 0.72})
    .encode(
        y=alt.Y("era:N", title=None, sort=eras, axis=alt.Axis(domain=False, ticks=False)),
        x=alt.X("share:Q", title=None, stack="normalize",
                axis=alt.Axis(format="%", values=[0, .25, .5, .75, 1])),
        color=alt.Color("source:N", title=None, sort=sources,
                        scale=alt.Scale(domain=sources, range=[BLUE, ORANGE, AQUA, AMBER])),
        order=alt.Order("source_order:Q"),
        tooltip=[alt.Tooltip("era:N", title="Era"), alt.Tooltip("source:N", title="Came from"),
                 alt.Tooltip("share:Q", title="Share of cast", format=".0%"),
                 alt.Tooltip("n:Q", title="Appearances")],
    )
    .transform_calculate(source_order=f"indexof({json.dumps(sources)}, datum.source)")
    .properties(height=260)
)
st.altair_chart(themed(stack), width="stretch")
note("Share of Challenge season appearances by where each player first became known. "
     "\"MTV's own shows\" includes Real World, Road Rules and Fresh Meat rookies.")

# ------------------------------------------------------------------ 2. return ticket
rookies = challenge[(challenge["show_appearance_number"] == 1) & (challenge["premiered_year"] <= 2023)
                    & challenge["finish_percentile"].notna()].copy()
rookies["returned"] = rookies["challenge_seasons"] > 1
rookies["first_result"] = pd.cut(
    rookies["finish_percentile"], [-0.01, 0.5, 1.01], labels=["Bottom half", "Top half"]).astype(str)
rookies.loc[rookies["made_final"], "first_result"] = "Made the final"
rookies.loc[rookies["is_winner"], "first_result"] = "Won"
by_result = rookies.groupby("first_result").agg(rate=("returned", "mean"), n=("person_id", "count")).reset_index()
by_bg = (rookies.groupby("background").agg(rate=("returned", "mean"), n=("person_id", "count"))
         .reset_index().query("n >= 20").sort_values("rate", ascending=False))
won_rate = by_result.set_index("first_result")["rate"].get("Won", float("nan"))
bottom_rate = by_result.set_index("first_result")["rate"].get("Bottom half", float("nan"))

chapter("Chapter 2", "The return ticket")
st.markdown(
    "Nobody signs a multi-season contract on The Challenge. Every rookie is auditioning for an "
    "invitation back, and the first season matters. But where you came from matters even more.")
pull(f"{pct(won_rate)} vs {pct(bottom_rate)}",
     f"Rookies who won their first Challenge were invited back {pct(won_rate)} of the time. "
     f"Those who finished in the bottom half: {pct(bottom_rate)}.")
order = ["Won", "Made the final", "Top half", "Bottom half"]
ticket = (
    alt.Chart(by_result)
    .mark_bar(color=BLUE, cornerRadiusEnd=4, height={"band": 0.62})
    .encode(
        y=alt.Y("first_result:N", title=None, sort=order, axis=alt.Axis(domain=False, ticks=False)),
        x=alt.X("rate:Q", title="Invited back for another season", axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip("first_result:N", title="First season"),
                 alt.Tooltip("rate:Q", title="Returned", format=".0%"),
                 alt.Tooltip("n:Q", title="Rookies")],
    )
    .properties(height=190, title=alt.Title("By how the first season went", anchor="start",
                                            color=INK_3, fontSize=12, fontWeight=500))
)
st.altair_chart(themed(ticket), width="stretch")

top_bg = by_bg.iloc[0]
low_bg = by_bg.iloc[-1]
st.markdown(
    f"Background is a bigger divide. **{top_bg['background']}** rookies came back "
    f"{pct(top_bg['rate'])} of the time; **{low_bg['background']}** rookies just {pct(low_bg['rate'])}.")
bg_chart = (
    alt.Chart(by_bg)
    .mark_bar(cornerRadiusEnd=4, height={"band": 0.62})
    .encode(
        y=alt.Y("background:N", title=None, sort="-x", axis=alt.Axis(domain=False, ticks=False)),
        x=alt.X("rate:Q", title="Invited back for another season", axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1])),
        color=alt.condition(alt.datum.background == low_bg["background"], alt.value(ORANGE), alt.value(BLUE)),
        tooltip=[alt.Tooltip("background:N", title="Background"),
                 alt.Tooltip("rate:Q", title="Returned", format=".0%"),
                 alt.Tooltip("n:Q", title="Rookies")],
    )
    .properties(height=34 * len(by_bg) + 30,
                title=alt.Title("By where they came from (20+ rookies)", anchor="start",
                                color=INK_3, fontSize=12, fontWeight=500))
)
st.altair_chart(themed(bg_chart), width="stretch")
note("Rookies whose first Challenge aired through 2023, so everyone has had time to be re-cast.")

# ------------------------------------------------------------------ 3. experience curve
def bucket(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, "4th–6th" if n <= 6 else "7th+")


vets = app.groupby(["person_id", "show_name"]).size().rename("k").reset_index().query("k >= 3")
curve = app.merge(vets[["person_id", "show_name"]], on=["person_id", "show_name"])
curve = curve[curve["show_name"].isin(["challenge", "survivor"])]
curve["season_n"] = curve["show_appearance_number"].map(bucket)
cv = (curve.groupby(["show_title", "season_n"])
      .agg(pctl=("finish_percentile", "mean"), n=("person_id", "count")).reset_index())
buckets = ["1st", "2nd", "3rd", "4th–6th", "7th+"]
cv = cv[cv["n"] >= 5]
ch_first = cv.query("show_title == 'The Challenge' and season_n == '1st'")["pctl"].iloc[0]
ch_last = cv.query("show_title == 'The Challenge'").set_index("season_n").reindex(buckets)["pctl"].dropna().iloc[-1]
sv_first = cv.query("show_title == 'Survivor' and season_n == '1st'")["pctl"].iloc[0]
sv_third = cv.query("show_title == 'Survivor' and season_n == '3rd'")["pctl"].iloc[0]

chapter("Chapter 3", "One show rewards experience. The other punishes it.")
st.markdown(
    "Follow the same players season after season and the two biggest shows split. Challenge "
    "veterans slowly get better. Survivor's returnees get worse, because everyone arrives "
    "knowing exactly who they are.")
pull(f"{sv_first:.2f} → {sv_third:.2f}",
     f"Survivor three-timers averaged a {sv_first:.2f} finish in their first season and {sv_third:.2f} "
     f"by their third. Challenge veterans climbed from {ch_first:.2f} to {ch_last:.2f}.")
line = alt.Chart(cv).encode(
    x=alt.X("season_n:N", title="Season on that show", sort=buckets, axis=alt.Axis(labelAngle=0)),
    y=alt.Y("pctl:Q", title="Average finish (1 = won, 0 = first out)", scale=alt.Scale(domain=[0.3, 0.8])),
    color=alt.Color("show_title:N", title=None, scale=alt.Scale(domain=["The Challenge", "Survivor"],
                                                                range=[BLUE, ORANGE])),
    tooltip=[alt.Tooltip("show_title:N", title="Show"), alt.Tooltip("season_n:N", title="Season"),
             alt.Tooltip("pctl:Q", title="Avg finish", format=".2f"), alt.Tooltip("n:Q", title="Players")],
)
labels = (alt.Chart(cv).transform_window(rank="rank()", sort=[alt.SortField("season_n", order="descending")],
                                         groupby=["show_title"])
          .mark_text(align="left", dx=10, fontSize=13, font="Inter", fontWeight=600)
          .encode(x=alt.X("season_n:N", sort=buckets), y="pctl:Q", text="show_title:N",
                  color=alt.Color("show_title:N", legend=None,
                                  scale=alt.Scale(domain=["The Challenge", "Survivor"], range=[BLUE, ORANGE])))
          .transform_filter("datum.season_n == '3rd' && datum.show_title == 'Survivor' || "
                            "datum.season_n == '7th+' && datum.show_title == 'The Challenge'"))
st.altair_chart(themed((line.mark_line(strokeWidth=2.5) + line.mark_point(size=80, filled=True, opacity=1)
                        + labels).properties(height=320)), width="stretch")
note("Only players with at least three seasons on that show, compared with themselves, so the "
     "climb isn't just weaker players dropping out. Points with fewer than 5 players are hidden.")

# ------------------------------------------------------------------ 4. home field
cross = app[app["person_id"].isin(person.loc[person["is_crossover"], "person_id"])]
hf = (cross.assign(home=cross["show_name"] == cross["debut_show"])
      .groupby(["person_id", "home"])["finish_percentile"].mean().unstack())
hf = hf.dropna()
hf.columns = ["away", "home"] if list(hf.columns) == [False, True] else hf.columns
better_home = int((hf["home"] > hf["away"]).sum())
hf_people = len(hf)
dfs = (cross[cross["show_name"] == cross["debut_show"]][["person_id", "debut_show"]]
       .drop_duplicates().merge(hf.reset_index(), on="person_id"))
dfs = dfs[dfs["debut_show"].isin(["survivor", "bigbrother"])]
db = (dfs.groupby("debut_show")[["home", "away"]].mean().reset_index()
      .melt(id_vars="debut_show", var_name="where", value_name="pctl"))
db["debut"] = db["debut_show"].map({"survivor": "Started on Survivor", "bigbrother": "Started on Big Brother"})
db["where"] = db["where"].map({"home": "On their original show", "away": "On other shows"})

chapter("Chapter 4", "There's no place like home")
st.markdown(
    "Crossover stars are recruited because they were great somewhere else. Most of them "
    "never quite match it on the new show.")
pull(f"{better_home} of {hf_people}",
     f"crossover players finished better, on average, on the show where they started.")
dumbbell_base = alt.Chart(db).encode(
    y=alt.Y("debut:N", title=None, axis=alt.Axis(domain=False, ticks=False)),
    x=alt.X("pctl:Q", title="Average finish (1 = won, 0 = first out)", scale=alt.Scale(domain=[0.3, 0.8])))
dumbbell = (
    dumbbell_base.mark_line(color=INK_3, strokeWidth=2).encode(detail="debut:N")
    + dumbbell_base.mark_point(size=180, filled=True, opacity=1, stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("where:N", title=None,
                        scale=alt.Scale(domain=["On their original show", "On other shows"],
                                        range=[ORANGE, BLUE])),
        tooltip=[alt.Tooltip("debut:N", title="Group"), alt.Tooltip("where:N", title="Where"),
                 alt.Tooltip("pctl:Q", title="Avg finish", format=".2f")])
).properties(height=170)
st.altair_chart(themed(dumbbell), width="stretch")
note("Some of the drop is luck evening out: people get recruited after an unusually good run, "
     "so their next result is likely to be closer to average wherever they play.")

# ------------------------------------------------------------------ 5. strategist penalty
tr = app[app["show_name"] == "traitors"].copy()
tr["group"] = ((tr["survivor_seasons"] + tr["bigbrother_seasons"]) > 0).map(
    {True: "Survivor & Big Brother alums", False: "Everyone else"})
rates = (tr.assign(traitor=tr["game_role"].eq("Traitor"), banished=tr["exit_method"].eq("banished"),
                   murdered=tr["exit_method"].eq("murdered"))
         .groupby("group")
         .agg(players=("person_id", "count"),
              **{"Cast as a Traitor": ("traitor", "mean"), "Banished": ("banished", "mean"),
                 "Murdered": ("murdered", "mean"), "Made the final": ("made_final", "mean")},
              wins=("is_winner", "sum")).reset_index())
r = rates.set_index("group")
alum_tr, else_tr = r.loc["Survivor & Big Brother alums", "Cast as a Traitor"], r.loc["Everyone else", "Cast as a Traitor"]

chapter("Chapter 5", "The strategist penalty")
st.markdown(
    "The Traitors hands its castle to known schemers, then watches what everyone else does "
    "with that reputation. Survivor and Big Brother alums are made Traitors far more often, "
    "and banished far more often. Almost none of them win.")
pull(f"{pct(alum_tr)} vs {pct(else_tr)}",
     f"of Survivor and Big Brother alums were cast as Traitors, against {pct(else_tr)} of everyone else. "
     f"Alums have won {int(r.loc['Survivor & Big Brother alums', 'wins'])} time(s); everyone else, "
     f"{int(r.loc['Everyone else', 'wins'])}.")
long = rates.melt(id_vars=["group", "players"],
                  value_vars=["Cast as a Traitor", "Banished", "Murdered", "Made the final"],
                  var_name="measure", value_name="rate")
groups = ["Survivor & Big Brother alums", "Everyone else"]
grouped = (
    alt.Chart(long).mark_bar(cornerRadiusEnd=4, stroke=SURFACE, strokeWidth=2)
    .encode(
        x=alt.X("measure:N", title=None, sort=["Cast as a Traitor", "Banished", "Murdered", "Made the final"],
                axis=alt.Axis(labelAngle=0, domain=False, ticks=False)),
        xOffset=alt.XOffset("group:N", sort=groups),
        y=alt.Y("rate:Q", title="Share of players", axis=alt.Axis(format="%")),
        color=alt.Color("group:N", title=None, sort=groups, scale=alt.Scale(domain=groups, range=[ORANGE, BLUE])),
        tooltip=[alt.Tooltip("group:N", title="Group"), alt.Tooltip("measure:N", title="Measure"),
                 alt.Tooltip("rate:Q", title="Share", format=".0%"),
                 alt.Tooltip("players:Q", title="Players in group")],
    ).properties(height=300)
)
st.altair_chart(themed(grouped), width="stretch")
note(f"{len(tr)} Traitors appearances across {tr['season_key'].nunique()} US seasons. Small samples: "
     "read these as a pattern worth watching, not proof.")

# ------------------------------------------------------------------ sidebar: quick facts
wins = app[app["is_winner"]].sort_values("premiered_date")
first_win = wins.groupby("person_id").first()[["premiered_date", "show_name"]].rename(
    columns={"premiered_date": "win_date", "show_name": "won_on"})
abroad = app.merge(first_win, left_on="person_id", right_index=True)
abroad = abroad[(abroad["premiered_date"] > abroad["win_date"]) & (abroad["show_name"] != abroad["won_on"])]
abroad = abroad.sort_values("premiered_date").groupby(["person_id", "show_name"]).first().reset_index()
champs_n, champs_won = len(abroad), int(abroad["is_winner"].sum())
champ_names = ", ".join(abroad.loc[abroad["is_winner"], "person_name"].tolist())
champ_names = f" ({champ_names})" if champ_names else ""

tr_winners = app[(app["show_name"] == "traitors") & app["is_winner"]].groupby("season_name")["game_role"].first()
traitor_seasons = int((tr_winners == "Traitor").sum())

careers = (app.groupby(["person_id", "person_name"])["premiered_year"].agg(["min", "max"]).reset_index())
careers["span"] = careers["max"] - careers["min"]
top_span = careers.sort_values(["span"], ascending=False).head(2)

html(f"""
<div class="sidebar">
  <h4>Quick facts</h4>
  <p class="fact"><b>Champions rarely repeat elsewhere.</b> Winners who tried a different show won
  again {champs_won} time(s) in {champs_n} attempts{champ_names}.</p>
  <p class="fact"><b>On The Traitors, the Traitors hold their own.</b> A Traitor took the win in
  {traitor_seasons} of {len(tr_winners)} US seasons.</p>
  <p class="fact"><b>The longest careers span {int(top_span['span'].iloc[0])} years:</b>
  {top_span['person_name'].iloc[0]} ({int(top_span['min'].iloc[0])}–{int(top_span['max'].iloc[0])}) and
  {top_span['person_name'].iloc[1]} ({int(top_span['min'].iloc[1])}–{int(top_span['max'].iloc[1])}).</p>
</div>
""")

# ------------------------------------------------------------------ explorer
chapter("Look anyone up", "Every season, every show")
st.markdown("Pick a player to see their whole career in order, across all four shows.")
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
if p["name_variants"] and " | " in p["name_variants"]:
    note(f"Billed under different names over the years: {p['name_variants']}.")

# ------------------------------------------------------------------ footer
html(f"""
<div class="footer">
<b>Methods.</b> Survivor data from the <a href="https://github.com/doehm/survivoR">survivoR</a> dataset (MIT);
Big Brother, The Challenge and The Traitors from Wikipedia season pages (CC BY-SA 4.0). US seasons only.
Each appearance was matched to one person with name normalization, blocking on the season a player
came from, similarity scoring, graph clustering and a hand-checked crosswalk. "Finish" is a size-adjusted
percentile: 1 = won, 0 = first out. The warehouse is rebuilt and tested on every change.
<br><br><a href="{REPO_URL}">Code, README and design decisions</a> &nbsp;·&nbsp;
<a href="{DOCS_URL}">dbt docs and lineage</a>
</div>
""")
