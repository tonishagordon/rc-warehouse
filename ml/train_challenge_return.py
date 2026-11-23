"""
Model 1: The Challenge "return ticket" (will a rookie be cast again?).

This is a churn / retention model in reality-TV clothing: predict whether a
first-time player gets invited back, from how their first season went and
where they came from.

- Data: marts.ml_challenge_rookies (built by dbt)
- Model: logistic regression (interpretable: every factor has one weight)
- Evaluation: grouped cross-validation by SEASON (a whole season is held out
  at a time, so the model never sees castmates of the players it's scoring),
  compared with a simple baseline (return rate by first-season result).
- Output: data/marts/ml_challenge_return_*.parquet for the app, and
  docs/model_cards/challenge_return.md

Usage (from the repo root, after dbt build):
    python ml/train_challenge_return.py
"""

import json
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "marts"
CARD = ROOT / "docs" / "model_cards" / "challenge_return.md"

NUMERIC = ["finish_percentile", "won_first_season", "made_final_first_season",
           "left_early_by_choice_or_rule", "cast_size", "premiered_year"]
CATEGORICAL = ["background_group"]
FRIENDLY = {
    "finish_percentile": "Finish in first season (higher = lasted longer)",
    "won_first_season": "Won their first season",
    "made_final_first_season": "Made the final in their first season",
    "left_early_by_choice_or_rule": "Quit, was removed or left for medical reasons",
    "cast_size": "Size of their first cast",
    "premiered_year": "Debut year (later = more recent)",
    "background_group_mtv_original": "Background: MTV original (Real World / Road Rules)",
    "background_group_survivor_bb": "Background: Survivor / Big Brother",
    "background_group_dating_show": "Background: dating show",
    "background_group_other": "Background: other",
}


def model() -> Pipeline:
    pre = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return Pipeline([("pre", pre), ("clf", LogisticRegression(C=0.5, max_iter=2000))])


def baseline_probs(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Return rate by first-season result bucket, learned on the training folds."""
    def bucket(d):
        return np.select([d.won_first_season == 1, d.made_final_first_season == 1, d.finish_percentile >= .5],
                         ["won", "final", "top_half"], "bottom_half")
    rates = train.assign(b=bucket(train)).groupby("b")["returned"].mean()
    return test.assign(b=bucket(test))["b"].map(rates).fillna(train["returned"].mean()).to_numpy()


def main() -> None:
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    df = con.sql("select * from marts.ml_challenge_rookies").df()
    con.close()

    known = df[df["label_known"]].reset_index(drop=True)
    future = df[~df["label_known"]].reset_index(drop=True)
    X, y, groups = known[NUMERIC + CATEGORICAL], known["returned"].astype(int), known["season_key"]

    # ---- honest evaluation: hold out whole seasons at a time
    oof_model, oof_base = np.zeros(len(known)), np.zeros(len(known))
    for train_idx, test_idx in GroupKFold(n_splits=5).split(X, y, groups):
        m = model().fit(X.iloc[train_idx], y.iloc[train_idx])
        oof_model[test_idx] = m.predict_proba(X.iloc[test_idx])[:, 1]
        oof_base[test_idx] = baseline_probs(known.iloc[train_idx], known.iloc[test_idx])

    metrics = {
        "trained_on": int(len(known)),
        "seasons": int(groups.nunique()),
        "base_rate": round(float(y.mean()), 3),
        "auc_model": round(float(roc_auc_score(y, oof_model)), 3),
        "auc_baseline": round(float(roc_auc_score(y, oof_base)), 3),
        "brier_model": round(float(brier_score_loss(y, oof_model)), 3),
        "brier_baseline": round(float(brier_score_loss(y, oof_base)), 3),
        "trained_date": date.today().isoformat(),
    }

    # ---- final model on all labelled rookies; explain + score recent rookies
    final = model().fit(X, y)
    names = final.named_steps["pre"].get_feature_names_out()
    names = [n.split("__", 1)[1] for n in names]
    coefs = pd.DataFrame({"feature": names, "weight": final.named_steps["clf"].coef_[0]})
    coefs["label"] = coefs["feature"].map(FRIENDLY).fillna(coefs["feature"])
    coefs = coefs.sort_values("weight", ascending=False)

    scored = future.assign(p_return=final.predict_proba(future[NUMERIC + CATEGORICAL])[:, 1])
    # has a 2024-26 rookie ALREADY been re-cast? (early check on the predictions)
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    seasons_now = con.sql("select person_id, challenge_seasons from marts.dim_person").df()
    con.close()
    scored = scored.merge(seasons_now, on="person_id", how="left")
    scored["already_back"] = scored["challenge_seasons"] > 1

    calib = (known.assign(p=oof_model, bin=pd.qcut(oof_model, 5, labels=False, duplicates="drop"))
             .groupby("bin").agg(predicted=("p", "mean"), actual=("returned", "mean"), n=("p", "size"))
             .reset_index())

    OUT.mkdir(parents=True, exist_ok=True)
    coefs.to_parquet(OUT / "ml_challenge_return_weights.parquet", index=False)
    scored[["person_id", "name_as_billed", "season_name", "premiered_year", "background",
            "finish_percentile", "p_return", "already_back"]].to_parquet(
        OUT / "ml_challenge_return_predictions.parquet", index=False)
    calib.to_parquet(OUT / "ml_challenge_return_calibration.parquet", index=False)
    (OUT / "ml_challenge_return_metrics.json").write_text(json.dumps(metrics, indent=2))

    CARD.parent.mkdir(parents=True, exist_ok=True)
    top = coefs.head(3)["label"].tolist()
    bottom = coefs.tail(2)["label"].tolist()
    CARD.write_text(f"""# Model card: The Challenge "return ticket"

**Question:** after a player's first season of The Challenge, will they ever be cast again?
**Type:** logistic regression (scikit-learn), standardized numeric features + one-hot background.
**Business analogue:** customer churn / retention.

## Data
- `marts.ml_challenge_rookies`: {metrics['trained_on']} rookie seasons across {metrics['seasons']} Challenge seasons (debuts through 2023, so everyone had time to be re-cast). Base rate: {metrics['base_rate']:.0%} returned.
- Features: first-season finish percentile, won / made the final, left by quitting/removal/medical, cast size, debut year, background group.
- Recent rookies (2024–2026) are scored, not trained on.

## Evaluation
Grouped 5-fold cross-validation by season: a whole season is held out at a time, so no castmates leak into training.

| | AUC (higher is better) | Brier score (lower is better) |
|---|---|---|
| Model | {metrics['auc_model']} | {metrics['brier_model']} |
| Baseline: return rate by first-season result | {metrics['auc_baseline']} | {metrics['brier_baseline']} |

## What drives the prediction
Strongest pushes toward a return: {', '.join(top)}.
Strongest pushes against: {', '.join(bottom)}.

## Limitations
- Casting is a producer decision driven by things the data can't see (storylines, availability, contracts, personal conflicts).
- Small groups (e.g. Survivor/Big Brother rookies) make those weights uncertain.
- "Returned" means appeared again on The Challenge in this warehouse's scope (main series + US spin-offs).

*Last trained {metrics['trained_date']} by `ml/train_challenge_return.py`.*
""")
    print(json.dumps(metrics, indent=2))
    print("\nWeights:\n", coefs[["label", "weight"]].to_string(index=False))
    print("\nRecent rookies most likely to return:\n",
          scored.sort_values("p_return", ascending=False)
          [["name_as_billed", "season_name", "p_return", "already_back"]].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
