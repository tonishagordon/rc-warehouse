"""
Model 2: Who wins Survivor? (as of the merge)

For every castaway who reaches the merge, estimate their chance of winning
from what was visible BEFORE the merge: their pre-merge game (votes against,
tribal councils, voting with the majority, challenge wins, advantages) and
their pre-merge edit (confessionals). Probabilities are normalized within
each season so they sum to 100%.

- Data: marts.ml_survivor_merge_features (built by dbt)
- Model: logistic regression (interpretable)
- Evaluation: leave-one-season-out: train on every other season, predict the
  held-out one, repeat for all completed seasons. Scored by how often the
  model's favorite actually won (top-1), how often the winner was in its top 3,
  and the winner's average rank. Compared with two baselines: picking at
  random, and picking whoever had the most pre-merge confessionals.
- Live: scores the season currently airing, among the players still in it.

Usage (from the repo root, after dbt build):
    python ml/train_survivor_winner.py
"""

import json
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "marts"
CARD = ROOT / "docs" / "model_cards" / "survivor_winner.md"

FEATURES = ["pre_confessional_index", "pre_confessionals", "pre_votes_against", "pre_tribals_attended",
            "pre_majority_vote_rate", "pre_challenge_win_rate", "pre_advantages_found",
            "age_at_filming", "prior_seasons"]
FRIENDLY = {
    "pre_confessional_index": "Edit: confessionals vs. expected (survivoR index)",
    "pre_confessionals": "Edit: total confessionals before the merge",
    "pre_votes_against": "Votes received before the merge",
    "pre_tribals_attended": "Tribal councils attended before the merge",
    "pre_majority_vote_rate": "Voted with the majority",
    "pre_challenge_win_rate": "Tribe's challenge win rate",
    "pre_advantages_found": "Advantages found before the merge",
    "age_at_filming": "Age",
    "prior_seasons": "Previous Survivor seasons (returnee)",
}


def model() -> Pipeline:
    return Pipeline([("scale", StandardScaler()),
                     ("clf", LogisticRegression(C=0.3, max_iter=2000))])


def normalize_within_season(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col] / df.groupby("season_key")[col].transform("sum")


def season_scores(df: pd.DataFrame, prob_col: str) -> dict:
    """Top-1, top-3 and mean rank of the actual winner, per held-out season."""
    ranks = df.groupby("season_key")[prob_col].rank(ascending=False, method="first")
    w = df.assign(rank=ranks)[df["won"] == 1]
    return {"top1": round(float((w["rank"] == 1).mean()), 3),
            "top3": round(float((w["rank"] <= 3).mean()), 3),
            "mean_winner_rank": round(float(w["rank"].mean()), 2)}


def main() -> None:
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    df = con.sql("select * from marts.ml_survivor_merge_features").df()
    con.close()
    df[FEATURES] = df[FEATURES].astype(float).fillna(df[FEATURES].astype(float).median())

    done = df[df["is_season_complete"] & df["won"].notna()].reset_index(drop=True)
    done = done[done.groupby("season_key")["won"].transform("sum") == 1].reset_index(drop=True)  # 1 winner/season
    live = df[~df["is_season_complete"]].reset_index(drop=True)
    X, y, groups = done[FEATURES], done["won"].astype(int), done["season_key"]

    oof = np.zeros(len(done))
    for tr, te in LeaveOneGroupOut().split(X, y, groups):
        oof[te] = model().fit(X.iloc[tr], y.iloc[tr]).predict_proba(X.iloc[te])[:, 1]
    done["p_model"] = oof
    done["p_model"] = normalize_within_season(done, "p_model")
    done["p_random"] = 1 / done["merge_size"]
    done["p_edit"] = done["pre_confessional_index"].rank(method="first")  # most-confessionals baseline

    metrics = {
        "seasons": int(groups.nunique()),
        "players_at_merge": int(len(done)),
        "model": season_scores(done, "p_model"),
        "baseline_most_confessionals": season_scores(done, "p_edit"),
        "baseline_random_expected_top1": round(float((1 / done.groupby("season_key").size()).mean()), 3),
        "trained_date": date.today().isoformat(),
    }

    final = model().fit(X, y)
    weights = pd.DataFrame({"feature": FEATURES, "weight": final.named_steps["clf"].coef_[0]})
    weights["label"] = weights["feature"].map(FRIENDLY)
    weights = weights.sort_values("weight", ascending=False)

    # held-out history: each completed season's pre-merge favorite and the actual winner
    fav = done.loc[done.groupby("season_key")["p_model"].idxmax(), ["season_key", "season_name", "full_name", "p_model"]]
    winner = done.loc[done["won"] == 1, ["season_key", "full_name", "p_model"]].rename(
        columns={"full_name": "winner", "p_model": "winner_p"})
    history = fav.rename(columns={"full_name": "favorite", "p_model": "favorite_p"}).merge(winner, on="season_key")
    history["season_number"] = history["season_key"].str[2:].astype(int)
    history = history.sort_values("season_number")

    live_out = pd.DataFrame()
    if len(live):
        live = live.assign(p_raw=final.predict_proba(live[FEATURES])[:, 1])
        live["p_at_merge"] = normalize_within_season(live, "p_raw")
        playing = live[live["still_in_game"]].copy()
        playing["p_now"] = playing["p_raw"] / playing["p_raw"].sum()
        live_out = live.merge(playing[["merge_player_key", "p_now"]], on="merge_player_key", how="left")
        live_out = live_out[["season_key", "season_name", "full_name", "castaway_short_name", "still_in_game",
                             "p_at_merge", "p_now"] + FEATURES].sort_values("p_at_merge", ascending=False)

    OUT.mkdir(parents=True, exist_ok=True)
    weights.to_parquet(OUT / "ml_survivor_winner_weights.parquet", index=False)
    history.to_parquet(OUT / "ml_survivor_winner_history.parquet", index=False)
    live_out.to_parquet(OUT / "ml_survivor_winner_live.parquet", index=False)
    (OUT / "ml_survivor_winner_metrics.json").write_text(json.dumps(metrics, indent=2))

    m, b = metrics["model"], metrics["baseline_most_confessionals"]
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(f"""# Model card: Who wins Survivor? (as of the merge)

**Question:** of the players who reach the merge, who is most likely to win?
**Type:** logistic regression (scikit-learn) on standardized features; probabilities normalized to sum to 100% within each season.

## Data
- `marts.ml_survivor_merge_features`: {metrics['players_at_merge']} players at the merge across {metrics['seasons']} completed US seasons.
- Only information from **before the merge episode**: votes received, tribals attended, voting with the majority, tribe challenge win rate, advantages found, confessionals (count and survivoR's standardized index), age, previous seasons.

## Evaluation (leave-one-season-out)
Each season is predicted by a model that never saw it.

| | Favorite actually won (top-1) | Winner in top 3 | Winner's average rank |
|---|---|---|---|
| Model | {m['top1']:.0%} | {m['top3']:.0%} | {m['mean_winner_rank']} |
| Baseline: most pre-merge confessionals | {b['top1']:.0%} | {b['top3']:.0%} | {b['mean_winner_rank']} |
| Baseline: random pick | {metrics['baseline_random_expected_top1']:.0%} | | |

## What drives the prediction
{chr(10).join(f"- {r.label}: {'raises' if r.weight > 0 else 'lowers'} the chance (weight {r.weight:+.2f})" for r in weights.itertuples())}

## Limitations
- Only ~1 winner per season, so ~{metrics['seasons']} positive examples: weights are noisy.
- The edit is a production choice, not gameplay; it predicts because editors know the ending.
- Twists (Edge of Extinction, Redemption Island, returnee formats) change the game in ways this model can't see.
- The live prediction uses only pre-merge information, even though the season has moved on since.

*Last trained {metrics['trained_date']} by `ml/train_survivor_winner.py`.*
""")
    print(json.dumps(metrics, indent=2))
    print("\nWeights:\n", weights[["label", "weight"]].to_string(index=False))
    if len(live_out):
        print("\nLive season (pre-merge information only):\n",
              live_out[["season_name", "full_name", "still_in_game", "p_at_merge", "p_now"]].to_string(index=False))


if __name__ == "__main__":
    main()
