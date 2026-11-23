# Model card: The Challenge "return ticket"

**Question:** after a player's first season of The Challenge, will they ever be cast again?
**Type:** logistic regression (scikit-learn), standardized numeric features + one-hot background.
**Business analogue:** customer churn / retention.

## Data
- `marts.ml_challenge_rookies`: 422 rookie seasons across 44 Challenge seasons (debuts through 2023, so everyone had time to be re-cast). Base rate: 47% returned.
- Features: first-season finish percentile, won / made the final, left by quitting/removal/medical, cast size, debut year, background group.
- Recent rookies (2024–2026) are scored, not trained on.

## Evaluation
Grouped 5-fold cross-validation by season: a whole season is held out at a time, so no castmates leak into training.

| | AUC (higher is better) | Brier score (lower is better) |
|---|---|---|
| Model | 0.65 | 0.235 |
| Baseline: return rate by first-season result | 0.528 | 0.251 |

## What drives the prediction
Strongest pushes toward a return: Background: MTV original (Real World / Road Rules), Finish in first season (higher = lasted longer), Background: Survivor / Big Brother.
Strongest pushes against: Made the final in their first season, Background: other.

## Limitations
- Casting is a producer decision driven by things the data can't see (storylines, availability, contracts, personal conflicts).
- Small groups (e.g. Survivor/Big Brother rookies) make those weights uncertain.
- "Returned" means appeared again on The Challenge in this warehouse's scope (main series + US spin-offs).

*Last trained 2026-11-23 by `ml/train_challenge_return.py`.*
