"""
Model 3: The Traitors season 5 scouting report.

Honest by design: the US Traitors has 4 seasons and 8 winners, which is far
too few to train a winner classifier. So instead of a black box, this uses
transparent track-record RATES with uncertainty:

- History: every past US Traitors player, grouped by their record BEFORE that
  season: Survivor/Big Brother alum, Challenge vet, or everyone else.
- For each group: how often they were cast as a Traitor, banished, murdered,
  reached the final, won. Each rate gets a Bayesian (Beta(1,1)) estimate and
  an 80% interval, so small groups show wide ranges instead of false precision.
- Season 5 cast: each player gets their group's rates, plus a track-record
  card if they're in this warehouse (Michele Fitzgerald, Taylor Hale, Jag
  Bains, Q Burdette, Rachel Robinson).

Usage (from the repo root, after dbt build):
    python ml/traitors_s5_scouting.py
"""

import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "marts"
CARD = ROOT / "docs" / "model_cards" / "traitors_s5_scouting.md"
TITLES = {"survivor": "Survivor", "bigbrother": "Big Brother", "challenge": "The Challenge",
          "traitors": "The Traitors"}
GROUPS = ["Survivor / Big Brother alum", "Challenge vet", "Everyone else"]
MEASURES = {"traitor": "Cast as a Traitor", "banished": "Banished", "murdered": "Murdered",
            "final": "Reached the end game", "won": "Won"}


def group_for(prior: pd.DataFrame) -> str:
    shows = set(prior["show_name"])
    if shows & {"survivor", "bigbrother"}:
        return GROUPS[0]
    if "challenge" in shows:
        return GROUPS[1]
    return GROUPS[2]


def rate(k: int, n: int) -> tuple[float, float, float]:
    a, b = 1 + k, 1 + n - k                     # Beta(1,1) prior + data
    return a / (a + b), beta.ppf(0.10, a, b), beta.ppf(0.90, a, b)


def main() -> None:
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    app = con.sql("select * from marts.fct_appearance").df()
    cast = con.sql("select * from marts.ml_traitors_s5_cast").df()
    con.close()
    app["premiered_date"] = pd.to_datetime(app["premiered_date"])

    # ---- history: each past Traitors player's group, from their record BEFORE that season
    tr = app[app["show_name"] == "traitors"].copy()
    tr["group"] = [
        group_for(app[(app["person_id"] == r.person_id) & (app["premiered_date"] < r.premiered_date)
                      & (app["show_name"] != "traitors")])
        for r in tr.itertuples()
    ]
    tr["traitor"] = tr["game_role"].eq("Traitor")
    tr["banished"] = tr["exit_method"].eq("banished")
    tr["murdered"] = tr["exit_method"].eq("murdered")
    tr["final"] = tr["made_final"]
    tr["won"] = tr["is_winner"]

    rows = []
    for g in GROUPS:
        sub = tr[tr["group"] == g]
        for m, label in MEASURES.items():
            k, n = int(sub[m].sum()), len(sub)
            mean, lo, hi = rate(k, n)
            rows.append(dict(group=g, measure=label, k=k, n=n, observed=k / n if n else None,
                             estimate=mean, low_80=lo, high_80=hi))
    group_rates = pd.DataFrame(rows)

    # ---- season 5: group + track record for each player
    cards = []
    for r in cast.itertuples():
        mine = app[app["person_id"] == r.person_id] if r.has_track_record else app.iloc[0:0]
        g = group_for(mine) if len(mine) else GROUPS[2]
        best = mine.sort_values(["finish_percentile"], ascending=False).head(1)
        gr = group_rates[group_rates["group"] == g].set_index("measure")
        cards.append(dict(
            name=r.name, known_for=r.known_for, group=g, has_track_record=bool(r.has_track_record),
            seasons=len(mine), shows=", ".join(sorted(mine["show_name"].map(TITLES).unique())),
            wins=int(mine["is_winner"].sum()), finals=int(mine["made_final"].sum()),
            avg_finish=float(mine["finish_percentile"].mean()) if len(mine) else None,
            best_season=(best["season_name"].iloc[0] if len(best) else None),
            best_result=(best["result_category"].iloc[0] if len(best) else None),
            p_traitor=gr.loc["Cast as a Traitor", "estimate"],
            p_traitor_low=gr.loc["Cast as a Traitor", "low_80"],
            p_traitor_high=gr.loc["Cast as a Traitor", "high_80"],
            p_banished=gr.loc["Banished", "estimate"],
            p_final=gr.loc["Reached the end game", "estimate"],
        ))
    scouting = pd.DataFrame(cards).sort_values(["has_track_record", "p_traitor", "seasons"],
                                               ascending=[False, False, False])

    history_counts = tr.groupby("group").size().reindex(GROUPS).fillna(0).astype(int).to_dict()
    traitors_per_season = round(float(tr.groupby("season_key")["traitor"].sum().mean()), 1)
    meta = {"past_seasons": int(tr["season_key"].nunique()), "past_players": int(len(tr)),
            "past_by_group": history_counts, "avg_traitors_per_season": traitors_per_season,
            "s5_cast": int(len(cast)), "s5_with_track_record": int(cast["has_track_record"].sum()),
            "built_date": date.today().isoformat()}

    OUT.mkdir(parents=True, exist_ok=True)
    group_rates.to_parquet(OUT / "ml_traitors_group_rates.parquet", index=False)
    scouting.to_parquet(OUT / "ml_traitors_s5_scouting.parquet", index=False)
    (OUT / "ml_traitors_s5_meta.json").write_text(json.dumps(meta, indent=2))

    t = group_rates[group_rates["measure"] == "Cast as a Traitor"].set_index("group")
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(f"""# Model card: The Traitors season 5 scouting report

**Question:** for the 23 announced season 5 players, how likely is each to be made a Traitor, and what does their track record say?
**Type:** Bayesian rate estimates (Beta(1,1) prior) by player group, with 80% intervals. **Not** a winner classifier.

## Why not predict the winner?
The US show has {meta['past_seasons']} seasons and 8 winners. A classifier trained on 8 positive examples would produce confident-looking numbers that are mostly noise. Group rates with honest uncertainty ranges are more useful and easier to defend.

## Data
- {meta['past_players']} past US Traitors appearances, grouped by each player's record **before** that season: {', '.join(f'{g}: {n}' for g, n in history_counts.items())}.
- Historically about {traitors_per_season} Traitors per season (including recruits).
- Season 5 cast: {meta['s5_cast']} players (Peacock, Sept 2026); {meta['s5_with_track_record']} have a track record in this warehouse.

## Cast as a Traitor, by group
| Group | Past players | Estimate | 80% range |
|---|---|---|---|
{chr(10).join(f"| {g} | {int(t.loc[g, 'n'])} | {t.loc[g, 'estimate']:.0%} | {t.loc[g, 'low_80']:.0%}–{t.loc[g, 'high_80']:.0%} |" for g in GROUPS)}

## Limitations
- Casting Traitors is a producer decision; past patterns can change any season.
- "Everyone else" mixes very different people (actors, athletes, Housewives); this warehouse has no record for them.
- Groups are small, so ranges are wide. That's the honest answer, not a flaw to hide.

*Built {meta['built_date']} by `ml/traitors_s5_scouting.py`.*
""")
    print(json.dumps(meta, indent=2))
    print("\nRates by group:\n", group_rates.round(3).to_string(index=False))
    print("\nSeason 5 players with a track record:\n",
          scouting[scouting["has_track_record"]][["name", "group", "seasons", "shows", "wins", "finals",
                                                  "avg_finish", "p_traitor", "p_traitor_low",
                                                  "p_traitor_high"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
