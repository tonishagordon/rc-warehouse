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

## D005 — Big Brother: extract → cell-level load → transform in dbt (ELT)
**Date:** 2026-11-21
**Decision:** Wikipedia pages are saved as dated snapshots (with revision IDs), then every table is flattened to one row per cell. dbt staging models rebuild the tables they need.
**Why:** Table layouts change across 28 seasons (merged cells, split double-eviction weeks, one-off twist tables). A cell-level raw layer never breaks on a layout change, parsing logic can change without re-downloading, and the snapshots make every build reproducible.

## D006 — Big Brother: classifying votes and results
**Date:** 2026-11-21
**Decisions:**
- BB01 has no Voting history table (Season 1 used audience "banishments"), so BB voting data starts at BB02. BB01 houseguests are still loaded.
- A voting cell counts as a **vote** only if its text exactly matches another houseguest's row label in the same season. Everything else is a status (HOH, nominated, evicted, no vote...) matched by pattern, or `other` (surfaced by a warn-level test).
- Row labels are nicknames ("Boogie", "Swaggy C"), while the HouseGuests table has full names. Matching the two is deferred to intermediate (within-show entity resolution).
- Result types were extended after the first build flagged 14 unrecognized values: banished (BB01), third place, exited (BB21 Camp Comeback), eliminated (BB27/BB28 battle-back twists), eviction nullified (BB25).
- After the second build, a warn-level test surfaced 54 unclassified cells. They were resolved as: non-voting statuses (Non-HouseGuest twins in BB5/BB17, Coach in BB14, Camp Director in BB21, Backstage in BB24, Saved in BB28); **two-target votes** (BB9 couples phase "Alex & Amanda", BB28's double-target week "Drew Haley"), which now match pairs of labels and split into two rows flagged `is_multi_target`; and a BB18 team-phase result row ("Frank 9 of 9 votes to evict") that is now recognized as an event row.
- BB04's last column is headed "Week 11", not "Finale", so its jury votes were counted as eviction votes. A column is now treated as the finale if its header says Finale **or** its result row says "votes to win".
- Houseguests with two result rows are mostly in-season returns (e.g. Amy BB3, Kaysar BB6, BB21's Camp Comeback). Staging keeps every row; intermediate picks the final outcome.
- Returning players' prior seasons are split out of the Name cell into `prior_shows_note`, a free signal for cross-show matching later.
