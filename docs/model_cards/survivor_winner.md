# Model card: Who wins Survivor? (as of the merge)

**Question:** of the players who reach the merge, who is most likely to win?
**Type:** logistic regression (scikit-learn) on standardized features; probabilities normalized to sum to 100% within each season.

## Data
- `marts.ml_survivor_merge_features`: 554 players at the merge across 49 completed US seasons.
- Only information from **before the merge episode**: votes received, tribals attended, voting with the majority, tribe challenge win rate, advantages found, confessionals (count and survivoR's standardized index), age, previous seasons.

## Evaluation (leave-one-season-out)
Each season is predicted by a model that never saw it.

| | Favorite actually won (top-1) | Winner in top 3 | Winner's average rank |
|---|---|---|---|
| Model | 26% | 45% | 4.39 |
| Baseline: most pre-merge confessionals | 18% | 39% | 4.76 |
| Baseline: random pick | 9% | | |

## What drives the prediction
- Edit: confessionals vs. expected (survivoR index): raises the chance (weight +0.60)
- Previous Survivor seasons (returnee): raises the chance (weight +0.16)
- Tribe's challenge win rate: raises the chance (weight +0.12)
- Tribal councils attended before the merge: raises the chance (weight +0.04)
- Advantages found before the merge: raises the chance (weight +0.03)
- Voted with the majority: raises the chance (weight +0.01)
- Edit: total confessionals before the merge: lowers the chance (weight -0.13)
- Age: lowers the chance (weight -0.17)
- Votes received before the merge: lowers the chance (weight -0.62)

## Limitations
- Only ~1 winner per season, so ~49 positive examples: weights are noisy.
- The edit is a production choice, not gameplay; it predicts because editors know the ending.
- Twists (Edge of Extinction, Redemption Island, returnee formats) change the game in ways this model can't see.
- The live prediction uses only pre-merge information, even though the season has moved on since.

*Last trained 2026-11-22 by `ml/train_survivor_winner.py`.*
