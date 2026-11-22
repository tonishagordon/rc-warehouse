# Design Decisions Log

A running record of modeling choices and why they were made.

---

## D001 — US seasons only for the MVP
**Date:** 2026-11-21
**Decision:** Survivor staging models filter `version = 'US'`. The raw layer keeps every version (US, AU, SA, UK, NZ).
**Why:** Crossover contestants (The Challenge, Big Brother, The Traitors) come from US shows. Keeping all versions in raw means international seasons can be added later by removing one filter.

## D002 — Demographic attributes excluded from the warehouse
**Date:** 2026-11-21
**Decision:** The source's race, ethnicity, LGBT and BIPOC columns in `castaway_details` are not carried past the raw layer.
**Why:** No planned analysis needs them, and leaving out sensitive personal attributes that aren't needed follows data-minimization practice. If a future analysis has a clear purpose for them, it would be added deliberately and documented here.

## D003 — Appearance grain = person x season
**Date:** 2026-11-21
**Decision:** `appearance_key = season_key || '_' || castaway_id`. Its uniqueness test is set to `warn`, not `error`.
**Why:** A player can have more than one row in a season (for example, re-entering the game). The warning measures how often this happens before the conformed `fct_appearance` model decides how to collapse those rows.
**Result (first build):** 0 warnings, so person x season is unique for US Survivor. The warning stays in place to catch it if other shows behave differently.

## D004 — In-progress seasons: placeholder jury rows excluded
**Date:** 2026-11-21
**Found by:** the `not_null` test on `stg_survivor__jury_votes.finalist_castaway_id` failed with 3 rows, all from US51 (jurors Kristin, Kilby and Lewis) with no finalist and no vote.
**Cause:** US51 is still airing. The source lists jurors as they're voted out, before the final Tribal Council, so their vote rows are placeholders.
**Decision:** Staging drops jury vote rows with no finalist. `stg_survivor__seasons` gets an `is_season_complete` flag (true once a winner exists), so analyses can include or exclude the airing season on purpose.
**Why not loosen the test:** the not-null check is right for completed votes. Filtering at the source of the problem keeps the test meaningful, and once the finale airs and the data refreshes, the real votes flow in with no code change.
