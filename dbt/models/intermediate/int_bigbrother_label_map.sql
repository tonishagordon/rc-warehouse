-- Big Brother voting tables label houseguests by the name used on air
-- ("Boogie", "Jag", "Da'Vonne"); the HouseGuests table has full names.
-- This maps each label to exactly one houseguest in the same season, trying
-- the strictest rule first:
--   1 label = full name      2 label = leading word(s) of the name
--   3 label is a whole word anywhere in the raw name (quoted nicknames)
--   4 label is a prefix of the name ("Dani" -> "Danielle ...")
--   5 first name + last initial ("Nicole A." -> "Nicole Anthony")
-- A label is kept only when its best rule picks a single houseguest; a second
-- pass retries ambiguous labels after removing houseguests already claimed.
-- Unmatched labels are listed by tests/assert_bb_labels_matched.sql (warn).

with labels as (
    select distinct season_key, row_label as label
    from {{ ref('stg_bigbrother__voting_grid') }}
    where not is_event_row and row_label is not null
),

houseguests as (
    select season_key, houseguest_name, any_value(houseguest_name_raw) as houseguest_name_raw
    from {{ ref('stg_bigbrother__houseguests') }}
    group by 1, 2
),

candidates as (
    select
        l.season_key,
        l.label,
        h.houseguest_name,
        case
            when {{ word_pad('l.label') }} = {{ word_pad('h.houseguest_name') }}                    then 1
            when starts_with({{ word_pad('h.houseguest_name') }}, {{ word_pad('l.label') }})         then 2
            when contains({{ word_pad('h.houseguest_name_raw') }}, {{ word_pad('l.label') }})        then 3
            when starts_with(lower(strip_accents(h.houseguest_name)), lower(strip_accents(l.label))) then 4
            -- first name + last initial, used when two houseguests share a first name
            -- ("Nicole A." / "Nicole F." in BB22, "Derek F." / "Derek X." in BB23)
            when regexp_matches(l.label, '^[^ ]+ [A-Za-z]\.?$')
             and lower(strip_accents(split_part(h.houseguest_name, ' ', 1)))
                 = lower(strip_accents(split_part(l.label, ' ', 1)))
             and starts_with(lower(strip_accents(string_split(h.houseguest_name, ' ')[-1])),
                             lower(regexp_extract(l.label, ' ([A-Za-z])\.?$', 1)))           then 5
        end as match_rule
    from labels as l
    inner join houseguests as h on h.season_key = l.season_key
),

best as (
    select *, min(match_rule) over (partition by season_key, label) as best_rule
    from candidates
    where match_rule is not null
),

-- pass 1: labels whose best rule picks exactly one houseguest
first_pass as (
    select season_key, label, any_value(houseguest_name) as houseguest_name, min(match_rule) as match_rule
    from best
    where match_rule = best_rule
    group by season_key, label
    having count(*) = 1
),

-- pass 2: for labels still ambiguous, set aside houseguests another label
-- already claimed, then try again. BB20: "Angela" matched Angela Rummans and
-- Angela "Rockstar" Lantry, but the "Rockstar" label already claims Lantry.
second_candidates as (
    select c.*
    from candidates as c
    where c.match_rule is not null
      and not exists (select 1 from first_pass as f
                      where f.season_key = c.season_key and f.label = c.label)
      and not exists (select 1 from first_pass as f
                      where f.season_key = c.season_key and f.houseguest_name = c.houseguest_name)
),

second_best as (
    select *, min(match_rule) over (partition by season_key, label) as best_rule
    from second_candidates
),

second_pass as (
    select season_key, label, any_value(houseguest_name) as houseguest_name, min(match_rule) as match_rule
    from second_best
    where match_rule = best_rule
    group by season_key, label
    having count(*) = 1
),

matched as (
    select *, 1 as match_pass from first_pass
    union all
    select *, 2 as match_pass from second_pass
)

select
    season_key,
    label,
    houseguest_name,
    match_rule,
    match_pass,
    'bigbrother|' || season_key || '|' || houseguest_name as mention_key
from matched
