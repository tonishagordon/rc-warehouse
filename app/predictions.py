"""The crystal ball: three predictive models built on the warehouse, one tab each."""

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from common import (AQUA, BLUE, DATA_DIR, INK, INK_3, ORANGE, REPO_URL, SURFACE, footer, html, note,
                    pct, pull, themed)

NICKNAMES = {"Angelica Loblack": "Jelly"}   # survivoR may not carry the name used on air yet


def on_air_name(full: str, short: str | None) -> str:
    """Survivor players by the name viewers know: Angelica "Jelly" Loblack."""
    words = full.split()
    if len(words) == 2 and words[0] == words[1]:          # survivoR placeholder, e.g. "Kilby Kilby"
        return words[0]
    nick = NICKNAMES.get(full) or short
    if nick and nick.lower() not in full.lower():
        return f'{words[0]} "{nick}" {" ".join(words[1:])}'
    return full


def ml_file(name: str) -> Path:
    return DATA_DIR / name


ML_READY = all(ml_file(f).exists() for f in [
    "ml_challenge_return_predictions.parquet", "ml_challenge_return_weights.parquet",
    "ml_challenge_return_metrics.json", "ml_survivor_winner_live.parquet",
    "ml_survivor_winner_history.parquet", "ml_survivor_winner_metrics.json",
    "ml_traitors_group_rates.parquet", "ml_traitors_s5_scouting.parquet", "ml_traitors_s5_meta.json"])

html("""
<div class="kicker">Predictions · Three models</div>
<div class="hero-title">The Crystal Ball</div>
<div class="deck">The same warehouse, looking forward. Each model was tested on seasons it never saw
and compared with a simple rule a fan might use instead. A model only earns its place by beating that rule.</div>
""")

if not ML_READY:
    st.info("Model outputs not found in data/marts/. Run `bash scripts/build_warehouse.sh` to train them.")
    st.stop()

c_pred = pd.read_parquet(ml_file("ml_challenge_return_predictions.parquet"))
c_w = pd.read_parquet(ml_file("ml_challenge_return_weights.parquet"))
c_m = json.loads(ml_file("ml_challenge_return_metrics.json").read_text())
s_live = pd.read_parquet(ml_file("ml_survivor_winner_live.parquet"))
s_hist = pd.read_parquet(ml_file("ml_survivor_winner_history.parquet"))
s_m = json.loads(ml_file("ml_survivor_winner_metrics.json").read_text())
t_rates = pd.read_parquet(ml_file("ml_traitors_group_rates.parquet"))
t_scout = pd.read_parquet(ml_file("ml_traitors_s5_scouting.parquet"))
t_meta = json.loads(ml_file("ml_traitors_s5_meta.json").read_text())

tab_s, tab_c, tab_t = st.tabs(["Survivor 51", "The Challenge", "The Traitors S5"])

with tab_c:
    # ---- The Challenge: who gets the call back?
    pull(pct(c_m["auc_model"]),
         f"Take one rookie who was invited back and one who wasn't: the model ranks the right one higher "
         f"{pct(c_m['auc_model'])} of the time. Going by first-season results alone gets it right "
         f"{pct(c_m['auc_baseline'])} of the time, and a coin flip 50%.")
    st.markdown(
        f"The model learned from {c_m['trained_on']:,} rookies across {c_m['seasons']} seasons and was graded on "
        "seasons it hadn't seen. Longer bars matter more. Where a rookie came from matters more than how they played.")
    c_w = c_w.assign(direction=c_w["weight"].gt(0).map({True: "Raises the chance", False: "Lowers the chance"}))
    weights_chart = (
        alt.Chart(c_w).mark_bar(cornerRadiusEnd=4, height={"band": 0.62})
        .encode(
            y=alt.Y("label:N", title=None, sort="-x", axis=alt.Axis(domain=False, ticks=False, labelLimit=0)),
            x=alt.X("weight:Q", title="← Less likely to be invited back · More likely →",
                    axis=alt.Axis(labels=False, ticks=False)),
            color=alt.Color("direction:N", title=None,
                            scale=alt.Scale(domain=["Raises the chance", "Lowers the chance"],
                                            range=[BLUE, ORANGE])),
            tooltip=[alt.Tooltip("label:N", title="Factor"), alt.Tooltip("direction:N", title="Effect")],
        ).properties(height=34 * len(c_w) + 40)
    )
    st.altair_chart(themed(weights_chart), width="stretch")

    recent = c_pred.sort_values("p_return", ascending=False).head(12).copy()
    recent["status"] = recent["already_back"].map({True: "Already invited back", False: "Still waiting"})
    recent["who"] = recent["name_as_billed"] + " · " + recent["season_name"]
    back_n = int(c_pred["already_back"].sum())
    st.markdown(
        f"**The early check.** The model scored the {len(c_pred)} rookies who debuted from 2024 on, "
        f"before knowing who'd be re-cast. {back_n} of them are already back.")
    rookie_chart = (
        alt.Chart(recent).mark_bar(cornerRadiusEnd=4, height={"band": 0.62})
        .encode(
            y=alt.Y("who:N", title=None, sort="-x", axis=alt.Axis(domain=False, ticks=False, labelLimit=0)),
            x=alt.X("p_return:Q", title="Predicted chance of a call back", axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("status:N", title=None,
                            scale=alt.Scale(domain=["Already invited back", "Still waiting"], range=[AQUA, BLUE])),
            tooltip=[alt.Tooltip("name_as_billed:N", title="Player"), alt.Tooltip("season_name:N", title="Debut"),
                     alt.Tooltip("background:N", title="Background"),
                     alt.Tooltip("p_return:Q", title="Predicted", format=".0%"),
                     alt.Tooltip("status:N", title="Status")],
        ).properties(height=30 * len(recent) + 40,
                     title=alt.Title("The 12 most likely, 2024–26 rookies", anchor="start",
                                     color=INK_3, fontSize=12, fontWeight=500))
    )
    st.altair_chart(themed(rookie_chart), width="stretch")



with tab_s:
    # ---- Survivor: who wins, judged at the merge?
    m, b = s_m["model"], s_m["baseline_most_confessionals"]
    pull(pct(m["top1"]),
         f"of the time, the model's pre-merge favorite went on to win, across {s_m['seasons']} seasons "
         f"it never trained on. Picking the player with the most confessionals: {pct(b['top1'])}. "
         f"A random pick: {pct(s_m['baseline_random_expected_top1'])}.")
    bench = pd.DataFrame({
        "method": ["This model", "Most confessionals (“the edit”)", "Random pick"],
        "rate": [m["top1"], b["top1"], s_m["baseline_random_expected_top1"]],
    })
    bench_chart = (
        alt.Chart(bench).mark_bar(cornerRadiusEnd=4, height={"band": 0.62})
        .encode(
            y=alt.Y("method:N", title=None, sort=list(bench["method"]),
                    axis=alt.Axis(domain=False, ticks=False, labelLimit=0)),
            x=alt.X("rate:Q", title="Pre-merge favorite actually won", axis=alt.Axis(format="%")),
            color=alt.condition(alt.datum.method == "This model", alt.value(ORANGE), alt.value(INK_3)),
            tooltip=[alt.Tooltip("method:N", title="Method"), alt.Tooltip("rate:Q", title="Hit rate", format=".0%")],
        ).properties(height=130)
    )
    st.altair_chart(themed(bench_chart), width="stretch")
    st.markdown(
        "The edit matters, but measured properly: survivoR's confessional index (airtime against what's "
        "expected) helps, while votes received before the merge hurt the most. Players who were nearly "
        "voted out early rarely win.")

    if len(s_live):
        playing = s_live[s_live["still_in_game"]].copy()
        playing["player"] = [on_air_name(f, s) for f, s in zip(playing["full_name"], playing["castaway_short_name"])]
        playing = playing.sort_values("p_now", ascending=False)
        lead = playing.iloc[0]
        season_title = playing["season_name"].iloc[0]
        st.markdown(f"**Live: {season_title}.** Odds for the {len(playing)} players still in the game, "
                    f"from what the model saw by the merge.")
        live_chart = (
            alt.Chart(playing).mark_bar(cornerRadiusEnd=4, height={"band": 0.62})
            .encode(
                y=alt.Y("player:N", title=None, sort="-x", axis=alt.Axis(domain=False, ticks=False, labelLimit=0)),
                x=alt.X("p_now:Q", title="Chance to win, among players still in the game", axis=alt.Axis(format="%")),
                color=alt.condition(alt.datum.player == lead["player"], alt.value(ORANGE), alt.value(BLUE)),
                tooltip=[alt.Tooltip("player:N", title="Player"),
                         alt.Tooltip("p_now:Q", title="Chance now", format=".0%"),
                         alt.Tooltip("p_at_merge:Q", title="Chance at the merge", format=".0%"),
                         alt.Tooltip("pre_votes_against:Q", title="Votes received pre-merge"),
                         alt.Tooltip("pre_confessional_index:Q", title="Confessional index", format=".2f")],
            ).properties(height=34 * len(playing) + 30)
        )
        st.altair_chart(themed(live_chart), width="stretch")
        note("The model only sees the season up to the merge. Idol plays, secret alliances and jury "
             "management after that are invisible to it, which is exactly where fans can out-predict it.")

    hist = s_hist.assign(called=s_hist["favorite"] == s_hist["winner"]).sort_values("season_number", ascending=False)
    with st.expander(f"Every past season: the model's favorite vs. the winner ({int(hist['called'].sum())} called)"):
        st.dataframe(
            hist[["season_name", "favorite", "favorite_p", "winner", "winner_p", "called"]]
            .rename(columns={"season_name": "Season", "favorite": "Pre-merge favorite", "favorite_p": "Their odds",
                             "winner": "Winner", "winner_p": "Winner's odds", "called": "Called it"}),
            hide_index=True, width="stretch",
            column_config={"Their odds": st.column_config.NumberColumn(format="percent"),
                           "Winner's odds": st.column_config.NumberColumn(format="percent")})



with tab_t:
    # ---- The Traitors season 5: who gets the cloak?
    traitor = t_rates[t_rates["measure"] == "Cast as a Traitor"].set_index("group")
    alum = traitor.loc["Survivor / Big Brother alum"]
    rest = traitor.loc["Everyone else"]
    pull(f"{pct(alum['estimate'])}",
         f"is the estimated chance a Survivor or Big Brother alum is made a Traitor, against "
         f"{pct(rest['estimate'])} for everyone else. With only {t_meta['past_seasons']} US seasons, "
         "the honest answer comes with a range.")
    st.markdown(
        f"Four seasons and eight winners are too few to train a winner model that means anything. So this "
        f"is a scouting report instead: how players with each kind of record have fared, with 80% ranges "
        f"that widen when the group is small. Season 5 has {t_meta['s5_cast']} players; "
        f"{t_meta['s5_with_track_record']} have a record in this warehouse.")
    t_groups = ["Survivor / Big Brother alum", "Challenge vet", "Everyone else"]
    t_measures = ["Cast as a Traitor", "Banished", "Reached the end game", "Won"]
    tr_plot = t_rates[t_rates["measure"].isin(t_measures)]
    enc = dict(
        y=alt.Y("measure:N", title=None, sort=t_measures, axis=alt.Axis(domain=False, ticks=False, labelLimit=0)),
        yOffset=alt.YOffset("group:N", sort=t_groups),
        color=alt.Color("group:N", title=None, sort=t_groups,
                        scale=alt.Scale(domain=t_groups, range=[ORANGE, AQUA, BLUE])),
        tooltip=[alt.Tooltip("group:N", title="Group"), alt.Tooltip("measure:N", title="Measure"),
                 alt.Tooltip("estimate:Q", title="Estimate", format=".0%"),
                 alt.Tooltip("low_80:Q", title="80% range from", format=".0%"),
                 alt.Tooltip("high_80:Q", title="80% range to", format=".0%"),
                 alt.Tooltip("k:Q", title="Times it happened"), alt.Tooltip("n:Q", title="Past players")],
    )
    ranges = alt.Chart(tr_plot).mark_rule(strokeWidth=3, opacity=0.55, strokeCap="round").encode(
        x=alt.X("low_80:Q", title="Estimated share of players", axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1])), x2="high_80:Q", **enc)
    points = alt.Chart(tr_plot).mark_circle(size=110, opacity=1, stroke=SURFACE, strokeWidth=2).encode(
        x="estimate:Q", **enc)
    board = alt.layer(ranges, points).properties(height=alt.Step(20))
    st.altair_chart(themed(board), width="stretch")
    note(f"{t_meta['past_players']} past US Traitors appearances, each grouped by the player's record "
         "before that season. The dot is the best estimate; the line is the range the true rate most likely "
         "falls in (80% confidence). Short lines mean more history to go on.")

    known = t_scout[t_scout["has_track_record"]]
    cards = "".join(
        f"""<div class="card">
          <div class="card-name">{r.name}</div>
          <div class="card-meta">{r.known_for}</div>
          <div class="card-stats"><span><b>{r.seasons}</b> seasons</span><span><b>{r.wins}</b> wins</span>
          <span><b>{r.finals}</b> finals</span></div>
          <div class="card-meta">Best run: {r.best_season or '—'}</div>
          <div class="card-odds">Traitor odds <b>{pct(r.p_traitor)}</b>
          <span>({pct(r.p_traitor_low)}–{pct(r.p_traitor_high)})</span></div>
        </div>""" for r in known.itertuples())
    if cards:
        st.markdown("**The players with a record here.** Their past seasons, and their group's odds of "
                    "being handed the cloak.")
        html(" ".join(f'<div class="cards">{cards}</div>'.split()))
    with st.expander(f"The full season 5 board (all {len(t_scout)} players)"):
        st.dataframe(
            t_scout[["name", "known_for", "group", "p_traitor", "p_traitor_low", "p_traitor_high", "p_final"]]
            .rename(columns={"name": "Player", "known_for": "Known for", "group": "Group",
                             "p_traitor": "Traitor odds", "p_traitor_low": "Low", "p_traitor_high": "High",
                             "p_final": "Reaches end game"}),
            hide_index=True, width="stretch",
            column_config={c: st.column_config.NumberColumn(format="percent")
                           for c in ["Traitor odds", "Low", "High", "Reaches end game"]})
    note("Producers choose the Traitors, so a pattern can change any season. Model cards with full "
         f'methods and limitations are in the <a href="{REPO_URL}/tree/main/docs/model_cards">repo</a>.')



footer(" Model methods, evaluation and limitations are in the "
       f'<a href="{REPO_URL}/tree/main/docs/model_cards">model cards</a>.')
