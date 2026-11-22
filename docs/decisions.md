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
- After the second build, a warn-level test surfaced 54 unclassified cells. They were resolved as: non-voting statuses (Non-HouseGuest twins in BB5/BB17, Coach in BB14, Camp Director in BB21, Backstage in BB24, Saved in BB28); **two-target votes** (BB9 couples phase "Alex & Amanda", BB28's double-target week "Drew Haley"), which now match pairs of labels and split into two rows flagged `is_multi_target`; BB14's coaches accepting or declining the offer to join the game (no vote); BB11's Coup d'État, kept as its own `power_used` status; and a BB18 team-phase result row ("Frank 9 of 9 votes to evict") that is now recognized as an event row.
- BB04's last column is headed "Week 11", not "Finale", so its jury votes were counted as eviction votes. A column is now treated as the finale if its header says Finale **or** its result row says "votes to win".
- Houseguests with two result rows are mostly in-season returns (e.g. Amy BB3, Kaysar BB6, BB21's Camp Comeback). Staging keeps every row; intermediate picks the final outcome.
- Returning players' prior seasons are split out of the Name cell into `prior_shows_note`, a free signal for cross-show matching later.

## D007 — The Challenge: appearances first, eliminations later
**Date:** 2026-11-21
**Decision:** Model who played each season, their original show and their finish first (from each season page's Contestants/Cast tables). Elimination charts (33 seasons, layout changes almost every season) come later.
**Why:** The Contestants tables carry an "Original season" column, which is exactly what links The Challenge to Survivor and Big Brother. That's the core of the project, so it's built before the hardest parsing.
**Details from the first build:**
- 4 seasons (Fresh Meat, The Ruins, Fresh Meat II, Battle of the Bloodlines) put their cast under sub-headings (e.g. Veterans / Rookies), so 0 contestants were found. For seasons with no Contestants/Cast section, any table with an "Original season" column is used instead.
- Finish values like "Episode 8" mean eliminated in episode 8; "Finalist" is its own type. Early seasons with no Finish column aren't tested for it.
- Champs vs. Pros/Stars use "Known for" / "Known From" instead of "Original season" (athletes and celebrities).
- Paired formats list two people per row with one Original season: Fresh Meat I/II pair an "Alumni" veteran with a "Fresh Meat" rookie, and Battle of the Bloodlines pairs an "Alumni" veteran with a "Bloodline" relative. The second person's origin is set from their column (rookie / relative new to TV), not copied from the veteran's.
- `origin_is_us_version` separates "Big Brother 20" from "Big Brother UK 17" or "Survivor Turkey 8": only US versions can link to this warehouse's Survivor and Big Brother data.
- The same person appears under different names across seasons (e.g. Faysal Shafaat vs. Faysal "Fessy" Shafaat). Resolving that is the entity-resolution step, not staging.

## D008 — Entity resolution, step 1: Challenge → origin season (blocked matching)
**Date:** 2026-11-21
**Decision:** Link each Challenge contestant whose Original season is a US Survivor or Big Brother season to a person in *that specific season*, all in dbt SQL:
- **Normalize names** (`normalize_name` macro): lowercase, strip accents, drop quoted nicknames and suffixes (Jr, III), remove punctuation. The nickname is kept separately.
- **Block** on the origin season ("Big Brother 20" → BB20; "Survivor: Cagayan" → its survivoR season key), so each contestant is compared with ~16–20 people instead of ~1,500.
- **Score** = best of exact name, first + last name, nickname + last name, and Jaro-Winkler similarity.
- **Decide:** `auto` if score ≥ 0.93 and ≥ 0.05 ahead of the runner-up; `review` if ≥ 0.80; otherwise `no_match`. Review cases go to a hand-maintained crosswalk (next step).
**Why:** Blocking on the origin season turns a fuzzy, error-prone global search into an easy pick within a small group. The margin rule stops a match from being accepted when two candidates look similar.
- *First results:* every match was automatic except 6 rows covering 3 people: Jay Starrett (survivoR: Justin Starrett), Shan Smith (Shantel Smith) and Tasha Fox (Latasha Fox). All three are correct matches; the players go by a shortened name. survivoR's `castaway` column holds that "goes by" name, so it's now used as the Survivor nickname, which lets the nickname + last-name rule match them automatically. A data-driven fix was preferred over hard-coding 3 overrides.
- *Build note:* the column was first named `show`, which is a reserved word in DuckDB (`SHOW TABLES`) and broke the first build. Renamed to `show_name`.

## D009 — dim_person: entity resolution as a graph
**Date:** 2026-11-21
**Decision:** Every piece of evidence that two records are the same person becomes an edge. People are the **connected components** of that graph, computed in dbt with a recursive CTE.
- **Same-show identity:** survivoR's `castaway_id`; within Big Brother and The Challenge, the same normalized full name or the same nickname + surname. Mentions connect to shared "identity nodes" (e.g. `chname:faysal shafaat`) instead of to each other, which keeps the edge count small.
- **Cross-show:** the automatic origin-season matches (D008).
- **Manual:** `seeds/crosswalk_manual.csv` for hand-checked links with no origin season to block on (e.g. Big Brother ↔ Survivor crossovers). A test fails if any row doesn't resolve to exactly one record on each side, so a typo can't slip through.
- **Single-word names are never merged by name**, since some early seasons list cast by first name only.
**Guards against over-merging:** a person can't hold two survivoR castaway IDs (error), and shouldn't appear twice in one season (warn).
**Review queue:** `int_crossover_candidates` lists same-surname pairs in different shows that weren't linked and look alike (≥ 0.90). Confirmed pairs move into the crosswalk seed.
**Why a graph:** evidence chains naturally. A Challenge vet linked to Big Brother 20 in one season automatically joins their other Challenge seasons and any Big Brother All-Stars return, with no need to compare every pair directly.

## D010 — Big Brother houseguests can point at their Survivor season too
**Date:** 2026-11-21
**Found by:** reviewing dim_person by eye. Dee Valladares (Survivor 45) showed no Big Brother season, although she played BB28 alongside Rick Devens (Survivor: Edge of Extinction). Nothing linked them: Big Brother records have no "Original season" column to block on.
**Decision:** Wikipedia lists returning players' earlier shows in the Big Brother Name cell (already split into `prior_shows_note`, D006). The first Survivor reference there ("Survivor 45", "Survivor: Edge of Extinction") becomes an `origin_season_key`, and the origin matcher (renamed `int_origin_matches`) now handles Big Brother sources as well as Challenge ones. Same blocking, scoring and thresholds.
**Fallback:** if a page doesn't list the earlier show, the pair shows up in the `int_crossover_candidates` review queue and is confirmed into `crosswalk_manual.csv`.

## D011 — Crosswalk seed: confirmed crossovers and reviewed non-matches
**Date:** 2026-11-21
**Decision:** `crosswalk_manual.csv` gets a `decision` column. `same` rows add a link; `different` rows record a pair that was reviewed and rejected, so it stops appearing in the review queue.
**Seeded from domain knowledge (project owner):** the five Big Brother ↔ Survivor crossovers: Cirie Fields (Survivor → BB25), Dee Valladares and Rick Devens (Survivor → BB28), Caleb Reynolds (BB16 → Survivor: Kaôh Rōng) and Hayden Moss (BB12 → Survivor: Blood vs. Water). BB → Survivor crossovers can't be found automatically: survivoR records don't list earlier shows.
**Also a verified test set:** these hand-confirmed pairs double as ground truth for measuring the automatic matcher (D010 should find the three Survivor → BB players on its own).
- *First review pass:* Natalie Anderson (Challenge: Double Agents) confirmed as the Survivor: San Juan del Sur winner. The Challenge lists her origin as The Amazing Race 23, so origin-season blocking couldn't find her. Six surname-only lookalikes (incl. two different Nick Browns) were marked `different`.
- *Seed schema change:* adding the `decision` column changes the seed's table shape, so the seed had to be reloaded with `dbt seed --full-refresh`. Without it, the seed load fails and the downstream marts keep stale data.
- *Rejections apply to people, not season pairs:* after the first pass, Nick Brown, Adria/Adam Klein and Nia/Nate Moore came back through their *other* seasons (e.g. Adam Klein's Winners at War season). `different` rows are now resolved to person IDs, so one review silences the pair for good.
- *Result:* 1,574 people from 2,762 appearances; 56 cross-show people; 0 over-merges; 80 dbt checks passing.
