# Model card: The Traitors season 5 scouting report

**Question:** for the 23 announced season 5 players, how likely is each to be made a Traitor, and what does their track record say?
**Type:** Bayesian rate estimates (Beta(1,1) prior) by player group, with 80% intervals. **Not** a winner classifier.

## Why not predict the winner?
The US show has 4 seasons and 8 winners. A classifier trained on 8 positive examples would produce confident-looking numbers that are mostly noise. Group rates with honest uncertainty ranges are more useful and easier to defend.

## Data
- 88 past US Traitors appearances, grouped by each player's record **before** that season: Survivor / Big Brother alum: 20, Challenge vet: 4, Everyone else: 64.
- Historically about 4.5 Traitors per season (including recruits).
- Season 5 cast: 23 players (Peacock, Sept 2026); 5 have a track record in this warehouse.

## Cast as a Traitor, by group
| Group | Past players | Estimate | 80% range |
|---|---|---|---|
| Survivor / Big Brother alum | 20 | 41% | 28%–54% |
| Challenge vet | 4 | 17% | 2%–37% |
| Everyone else | 64 | 17% | 11%–23% |

## Limitations
- Casting Traitors is a producer decision; past patterns can change any season.
- "Everyone else" mixes very different people (actors, athletes, Housewives); this warehouse has no record for them.
- Groups are small, so ranges are wide. That's the honest answer, not a flaw to hide.

*Built 2026-11-23 by `ml/traitors_s5_scouting.py`.*
