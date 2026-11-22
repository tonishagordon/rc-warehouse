-- Entity resolution, step 2: every piece of evidence that two mentions are
-- the same person, as graph edges. int_person_clusters turns connected
-- groups into one person.
--
-- Mentions connect to "identity nodes" rather than to each other:
--   survivor     -> surv:<castaway_id>            (survivoR already resolved returnees)
--   bigbrother   -> bbname:<normalized full name>  (+ bbname:<nickname> <last name>)
--   challenge    -> chname:<normalized full name>  (+ chname:<nickname> <last name>)
-- so "Faysal \"Fessy\" Shafaat" and "Faysal Shafaat" meet at chname:faysal shafaat,
-- and "Chris \"CT\" Tamburello" and "CT Tamburello" meet at chname:ct tamburello.
-- Single-word names (early seasons list some cast by first name only) are
-- never merged by name: too many different "Mark"s.
--
-- Cross-show edges come from the blocked origin-season matcher (D008) and
-- the hand-checked seed crosswalk_manual.csv.
with m as (
    select * from {{ ref('int_person_mentions') }}
),

identity_edges as (
    select mention_key as a, 'surv:' || source_person_id as b, 'survivor_castaway_id' as edge_type
    from m where show_name = 'survivor'

    union all
    select mention_key,
           case show_name when 'bigbrother' then 'bbname:' when 'traitors' then 'trname:' else 'chname:' end || name_norm,
           'same_show_full_name'
    from m
    where show_name in ('bigbrother', 'challenge', 'traitors')
      and name_norm like '% %'

    union all
    select mention_key,
           case show_name when 'bigbrother' then 'bbname:' when 'traitors' then 'trname:' else 'chname:' end
               || nickname_norm || ' ' || last_name_norm,
           'same_show_nickname'
    from m
    where show_name in ('bigbrother', 'challenge', 'traitors')
      and nickname_norm is not null
      and last_name_norm is not null
      and name_norm like '% %'
),

-- Traitors <-> Challenge: Traitors lists a Challenge vet by their ORIGINAL
-- show ("The Real World: Key West"), exactly as the Challenge pages do. Same
-- full name + the same origin note = same person. (D013)
traitors_challenge_edges as (
    select t.mention_key as a, c.mention_key as b, 'shared_origin_note' as edge_type
    from m as t
    inner join m as c
        on c.show_name = 'challenge'
       and c.name_norm = t.name_norm
       and lower(strip_accents(c.prior_shows_note)) = lower(strip_accents(t.prior_shows_note))
    where t.show_name = 'traitors'
      and t.name_norm like '% %'
),

cross_show_edges as (
    select source_mention_key as a, candidate_mention_key as b, 'origin_season_match' as edge_type
    from {{ ref('int_origin_matches') }}
    where match_decision = 'auto'
),

seed as (
    -- only confirmed links; 'different' rows just silence the review queue
    select * from {{ ref('crosswalk_manual') }}
    where lower(decision) = 'same'
),

manual_edges as (
    select ma.mention_key as a, mb.mention_key as b, 'manual_crosswalk' as edge_type
    from seed as s
    inner join m as ma
        on ma.show_name = s.show_a
       and ma.season_key = s.season_a
       and ma.name_norm = {{ normalize_name('s.name_a') }}
    inner join m as mb
        on mb.show_name = s.show_b
       and mb.season_key = s.season_b
       and mb.name_norm = {{ normalize_name('s.name_b') }}
)

select * from identity_edges
union all
select * from traitors_challenge_edges
union all
select * from cross_show_edges
union all
select * from manual_edges
