"""Game moves: do idols, votes and competition wins actually lead to winning?"""

import altair as alt
import pandas as pd
import streamlit as st

from common import BLUE, DATA_DIR, ORANGE, footer, html, note, pct, pull, themed

MEASURES = {"made_final": "Made the final", "is_winner": "Won"}

html("""
<div class="kicker">Game moves · Survivor and Big Brother</div>
<div class="hero-title">Do the Big Moves Pay Off?</div>
<div class="deck">Fans love an idol play and a competition streak. Here is how often those moves
turn into a spot in the final, or the win.</div>
""")

files = {n: DATA_DIR / f"{n}.parquet" for n in ["mart_survivor_moves", "mart_bigbrother_moves"]}
if not all(f.exists() for f in files.values()):
    st.info("Game-move data not found in data/marts/. Run `bash scripts/build_warehouse.sh` first.")
    st.stop()


@st.cache_data
def load_moves():
    return pd.read_parquet(files["mart_survivor_moves"]), pd.read_parquet(files["mart_bigbrother_moves"])


def rates(df: pd.DataFrame, bucket: str, order: list[str]) -> pd.DataFrame:
    g = df.groupby(bucket, observed=True).agg(made_final=("made_final", "mean"), is_winner=("is_winner", "mean"),
                                              players=("made_final", "size")).reset_index()
    g = g[g[bucket].isin(order)]
    return g.melt(id_vars=[bucket, "players"], value_vars=list(MEASURES), var_name="measure", value_name="rate") \
            .assign(measure=lambda d: d["measure"].map(MEASURES))


def rate_bars(long: pd.DataFrame, bucket: str, order: list[str], x_title: str) -> alt.Chart:
    measures = list(MEASURES.values())
    return (
        alt.Chart(long).mark_bar(cornerRadiusEnd=4, stroke="#1a1a19", strokeWidth=2)
        .encode(
            x=alt.X(f"{bucket}:N", title=x_title, sort=order, axis=alt.Axis(labelAngle=0, domain=False, ticks=False)),
            xOffset=alt.XOffset("measure:N", sort=measures),
            y=alt.Y("rate:Q", title="Share of players", axis=alt.Axis(format="%")),
            color=alt.Color("measure:N", title=None, sort=measures, scale=alt.Scale(domain=measures, range=[BLUE, ORANGE])),
            tooltip=[alt.Tooltip(f"{bucket}:N", title=x_title), alt.Tooltip("measure:N", title="Measure"),
                     alt.Tooltip("rate:Q", title="Share", format=".0%"), alt.Tooltip("players:Q", title="Players")],
        ).properties(height=260)
    )


def rate_of(long: pd.DataFrame, bucket: str, value: str, measure: str = "Won") -> float:
    row = long[(long[bucket] == value) & (long["measure"] == measure)]
    return float(row["rate"].iloc[0]) if len(row) else float("nan")


def stat_row(items: list[tuple[str, str]]) -> None:
    html('<div class="stats" style="margin:1.2rem 0 1.4rem">' + "".join(
        f'<div><div class="stat-num">{v}</div><div class="stat-label">{label}</div></div>' for v, label in items)
        + "</div>")


sv, bb = load_moves()
st.markdown("**How to read the charts:** each pair of bars is one group of players. Blue is the share "
            "of that group who made the final; orange is the share who won.")
tab_s, tab_b = st.tabs(["Survivor", "Big Brother"])

# ------------------------------------------------------------------ Survivor
with tab_s:
    s = sv[sv["is_season_complete"] & sv["season_has_idols"] & sv["finish_percentile"].notna()].copy()
    n_seasons = s["season_key"].nunique()

    html('<div class="subhead">Finders keepers?</div>')
    idol_order = ["None", "One", "Two or more"]
    s["idols"] = pd.cut(s["idols_held"], [-1, 0, 1, 99], labels=idol_order).astype(str)
    finders = rates(s, "idols", idol_order)
    pull(f"{pct(rate_of(finders, 'idols', 'Two or more'))} vs {pct(rate_of(finders, 'idols', 'None'))}",
         f"Players who held two or more idols won {pct(rate_of(finders, 'idols', 'Two or more'))} of the time. "
         f"Players who never held one: {pct(rate_of(finders, 'idols', 'None'))}.")
    st.altair_chart(themed(rate_bars(finders, "idols", idol_order, "Idols held in a season")), width="stretch")
    note(f"{len(s):,} players in the {n_seasons} completed seasons that had idols. Players who last longer get "
         "more chances to find one, so idols and long runs feed each other: this is a pattern, not proof.")

    html('<div class="subhead">Does playing it work?</div>')
    plays = int(s["idol_plays"].sum())
    cancelled = int(s["idol_plays_cancelling_votes"].sum())
    stat_row([(f"{plays}", "times an idol was played"),
              (pct(cancelled / plays) if plays else "–", "of those plays actually cancelled votes"),
              (f"{int(s['votes_cancelled'].sum())}", "votes cancelled by idols in total"),
              (f"{int(s['voted_out_holding_idol'].sum())}", "players voted out with an idol in their pocket")])
    st.markdown(
        f"The other {pct(1 - cancelled / plays) if plays else '–'} were played when nobody was voting for "
        f"that player, usually as insurance. {int(s['idol_plays_for_others'].sum())} plays protected someone "
        "other than the person holding the idol.")

    html('<div class="subhead">Being on the right side of the vote</div>')
    st.markdown(
        "At every Tribal Council, a player's vote either goes to the person who gets voted out (they were "
        "**on the right side**) or to someone who stays (they were **left out of the plan**). Players who "
        "are usually on the right side tend to be in the alliance making the decisions.")
    v = s[s["votes_cast"] >= 4].copy()
    vote_order = ["Less than half the time", "Half to 3 in 4 times", "3 in 4 times or more"]
    v["side"] = pd.cut(v["majority_vote_rate"], [-0.01, 0.4999, 0.7499, 1.01], labels=vote_order).astype(str)
    steer = rates(v, "side", vote_order)
    pull(f"{pct(rate_of(steer, 'side', '3 in 4 times or more'))} vs "
         f"{pct(rate_of(steer, 'side', 'Less than half the time'))}",
         f"Players on the right side of the vote at least 3 in 4 times won "
         f"{pct(rate_of(steer, 'side', '3 in 4 times or more'))} of the time. Players on the right side "
         f"less than half the time won {pct(rate_of(steer, 'side', 'Less than half the time'))}.")
    st.altair_chart(themed(rate_bars(steer, "side", vote_order, "How often they were on the right side")),
                    width="stretch")
    note(f"{len(v):,} players who voted at least 4 times. Neither show's data records alliances, so being "
         "on the right side of the vote stands in for being part of the majority.")

# ------------------------------------------------------------------ Big Brother
with tab_b:
    b = bb[bb["season_has_veto"] & bb["finish_percentile"].notna()].copy()

    html('<div class="subhead">Comp beasts vs. floaters</div>')
    comp_order = ["0", "1–2", "3–4", "5 or more"]
    b["comps"] = pd.cut(b["comp_wins"], [-1, 0, 2, 4, 99], labels=comp_order).astype(str)
    comps = rates(b, "comps", comp_order)
    st.markdown("Each Head of Household (HOH) or Power of Veto win counts as one competition win.")
    pull(pct(rate_of(comps, "comps", "5 or more", "Made the final")),
         f"of houseguests who won 5 or more competitions in a season made the final. Of those who never "
         f"won one, {pct(rate_of(comps, 'comps', '0', 'Made the final'))} did.")
    st.altair_chart(themed(rate_bars(comps, "comps", comp_order, "Competition wins in the season (HOH + Veto)")), width="stretch")
    top = b.sort_values("comp_wins", ascending=False).head(1).iloc[0]
    note(f"{len(b):,} houseguests across {b['season_key'].nunique()} seasons with the Veto. Most in one season: "
         f"{top['houseguest_name']} ({top['season_name']}), {int(top['hoh_wins'])} HOH and {int(top['veto_wins'])} Veto wins.")

    html('<div class="subhead">Life on the block</div>')
    block_order = ["Never", "Once", "Twice", "3 or more times"]
    b["block"] = pd.cut(b["weeks_nominated"], [-1, 0, 1, 2, 99], labels=block_order).astype(str)
    block = rates(b, "block", block_order)
    winners = b[b["is_winner"]]
    pull(f"{int((winners['weeks_nominated'] > 0).sum())} of {len(winners)}",
         "Big Brother winners were nominated for eviction at least once on their way to the win.")
    st.altair_chart(themed(rate_bars(block, "block", block_order, "Weeks nominated for eviction")), width="stretch")
    note("A week counts if the houseguest was nominated for eviction at any point that week, even if the "
         "Veto later took them off the block. Houseguests who last longer have more weeks to be nominated.")

footer()
