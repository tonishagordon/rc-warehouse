-- Every appearance of a person in any show, in one shape, with normalized
-- names (Survivor, Big Brother, The Challenge, The Traitors). This is the
-- input to entity resolution: "who is the same person?"
--
-- Grain: one row per person per season per show.
-- origin_season_key points at an earlier season the person came from, when
-- it's in this warehouse: Challenge "Original season", or a Survivor season
-- listed on a Big Brother houseguest's name (e.g. BB28's Survivor players)
-- (e.g. 'BB20', 'US28').
with survivor as (
    select
        'survivor|' || appearance_key       as mention_key,
        'survivor'                          as show_name,
        season_key,
        castaway_id                         as source_person_id,
        full_name                           as display_name,
        {{ normalize_name('full_name') }}   as name_norm,
        -- survivoR's short name is what the player goes by ("Jay" for Justin
        -- Starrett, "Shan" for Shantel Smith). Use it as the nickname when it
        -- differs from the legal first name.
        coalesce(
            {{ nickname('full_name') }},
            nullif({{ normalize_name('castaway_short_name') }},
                   split_part({{ normalize_name('full_name') }}, ' ', 1))
        )                                   as nickname_norm,
        cast(null as varchar)               as origin_season_key,
        cast(null as varchar)               as prior_shows_note
    from {{ ref('stg_survivor__castaways') }}
),

bigbrother_raw as (
    -- a houseguest can have 2 result rows in a season (returns); one mention each
    select distinct
        season_key,
        houseguest_name,
        prior_shows_note,
        -- Returning players list earlier shows in the Name cell, e.g.
        -- "Survivor 45" or "Survivor: Edge of Extinction". Keep the first
        -- Survivor reference as an origin pointer (one is enough to link).
        trim(regexp_extract(prior_shows_note, '(Survivor(?: \d+|: [^&,]+))', 1)) as survivor_ref
    from {{ ref('stg_bigbrother__houseguests') }}
),

survivor_seasons as (
    select season_key, lower(strip_accents(season_name)) as season_name_norm
    from {{ ref('stg_survivor__seasons') }}
),

bigbrother as (
    select
        'bigbrother|' || b.season_key || '|' || b.houseguest_name as mention_key,
        'bigbrother'                                    as show_name,
        b.season_key,
        cast(null as varchar)                           as source_person_id,
        b.houseguest_name                               as display_name,
        {{ normalize_name('b.houseguest_name') }}       as name_norm,
        {{ nickname('b.houseguest_name') }}             as nickname_norm,
        case
            when nullif(b.survivor_ref, '') is not null
                then coalesce(
                    ss.season_key,
                    case when regexp_matches(b.survivor_ref, '^Survivor \d+$')
                         then 'US' || lpad(regexp_extract(b.survivor_ref, '(\d+)', 1), 2, '0') end)
        end                                             as origin_season_key,
        b.prior_shows_note
    from bigbrother_raw as b
    left join survivor_seasons as ss
        on lower(strip_accents(b.survivor_ref)) = ss.season_name_norm
),

challenge as (
    select
        'challenge|' || c.contestant_key                as mention_key,
        'challenge'                                     as show_name,
        c.season_key,
        cast(null as varchar)                           as source_person_id,
        c.contestant_name                               as display_name,
        {{ normalize_name('c.contestant_name') }}       as name_norm,
        {{ nickname('c.contestant_name') }}             as nickname_norm,
        case
            -- "Big Brother 20" (US only) -> BB20
            when c.origin_show = 'Big Brother' and c.origin_is_us_version
             and regexp_matches(c.original_season, '^Big Brother \d+$')
                then 'BB' || lpad(regexp_extract(c.original_season, '(\d+)', 1), 2, '0')
            -- "Survivor: Cagayan" -> season name lookup; "Survivor 41" -> US41
            when c.origin_show = 'Survivor' and c.origin_is_us_version
                then coalesce(
                    ss.season_key,
                    case when regexp_matches(c.original_season, '^Survivor \d+$')
                         then 'US' || lpad(regexp_extract(c.original_season, '(\d+)', 1), 2, '0') end)
        end                                             as origin_season_key,
        c.original_season                               as prior_shows_note
    from {{ ref('stg_challenge__contestants') }} as c
    left join survivor_seasons as ss
        on lower(strip_accents(c.original_season)) = ss.season_name_norm
),

traitors as (
    select
        'traitors|' || t.contestant_key                 as mention_key,
        'traitors'                                      as show_name,
        t.season_key,
        cast(null as varchar)                           as source_person_id,
        t.contestant_name                               as display_name,
        {{ normalize_name('t.contestant_name') }}       as name_norm,
        {{ nickname('t.contestant_name') }}             as nickname_norm,
        -- Notability "Big Brother 14" / "Survivor: Cook Islands" -> that season
        case
            when t.origin_show = 'Big Brother' and t.origin_is_us_version
             and regexp_matches(t.notability, '^Big Brother \d+$')
                then 'BB' || lpad(regexp_extract(t.notability, '(\d+)', 1), 2, '0')
            when t.origin_show = 'Survivor' and t.origin_is_us_version
                then coalesce(
                    ss.season_key,
                    case when regexp_matches(t.notability, '^Survivor \d+$')
                         then 'US' || lpad(regexp_extract(t.notability, '(\d+)', 1), 2, '0') end)
        end                                             as origin_season_key,
        t.notability                                    as prior_shows_note
    from {{ ref('stg_traitors__contestants') }} as t
    left join survivor_seasons as ss
        on lower(strip_accents(t.notability)) = ss.season_name_norm
),

unioned as (
    select * from survivor
    union all
    select * from bigbrother
    union all
    select * from challenge
    union all
    select * from traitors
)

select
    *,
    split_part(name_norm, ' ', 1)                                      as first_name_norm,
    -- last token as surname ("cliff hogg" -> "hogg")
    regexp_extract(name_norm, '([a-z]+)$', 1)                          as last_name_norm
from unioned
