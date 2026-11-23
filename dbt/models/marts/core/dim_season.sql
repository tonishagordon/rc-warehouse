-- One row per season of every show, with dates and cast size.
with survivor as (
    select
        season_key,
        'survivor'                      as show_name,
        'Survivor'                      as series,
        season_number,
        season_name,
        premiered_date,
        ended_date                      as finale_date,
        is_season_complete
    from {{ ref('stg_survivor__seasons') }}
),

bigbrother as (
    select
        h.season_key,
        'bigbrother'                    as show_name,
        'Big Brother'                   as series,
        max(h.season_number)            as season_number,
        'Big Brother ' || cast(max(h.season_number) as varchar) as season_name,
        p.premiered_date,
        p.finale_date,
        bool_or(h.result_type = 'winner') as is_season_complete
    from {{ ref('stg_bigbrother__houseguests') }} as h
    left join {{ ref('int_season_premieres') }} as p
        on p.show_name = 'bigbrother' and p.season_key = h.season_key
    group by h.season_key, p.premiered_date, p.finale_date
),

challenge_winners as (
    select season_key, bool_or(finish_type = 'winner') as has_winner
    from {{ ref('stg_challenge__contestants') }}
    group by season_key
),

challenge as (
    select
        s.season_key,
        'challenge'                     as show_name,
        s.series,
        s.season_number,
        -- spin-offs are titled by number on Wikipedia ("5"): prefix the series
        case
            when regexp_matches(s.season_title, '^\d+$') then s.series || ' ' || s.season_title
            when s.season_key like 'CUSA%'                then 'The Challenge: USA season ' || cast(cast(substr(s.season_key, 5) as integer) as varchar)
            else s.season_title
        end                             as season_name,
        p.premiered_date,
        p.finale_date,
        coalesce(w.has_winner, false)   as is_season_complete
    from {{ ref('stg_challenge__seasons') }} as s
    left join {{ ref('int_season_premieres') }} as p
        on p.show_name = 'challenge' and p.season_key = s.season_key
    left join challenge_winners as w
        on w.season_key = s.season_key
),

traitors as (
    select
        s.season_key,
        'traitors'                      as show_name,
        'The Traitors'                  as series,
        s.season_number,
        s.season_name,
        p.premiered_date,
        p.finale_date,
        bool_or(c.finish_type = 'winner') as is_season_complete
    from {{ ref('stg_traitors__seasons') }} as s
    left join {{ ref('int_season_premieres') }} as p
        on p.show_name = 'traitors' and p.season_key = s.season_key
    left join {{ ref('stg_traitors__contestants') }} as c
        on c.season_key = s.season_key
    group by all
),

seasons as (
    select * from survivor
    union all select * from bigbrother
    union all select * from challenge
    union all select * from traitors
),

cast_sizes as (
    select show_name, season_key, count(distinct person_id) as cast_size
    from {{ ref('bridge_person_mention') }}
    group by show_name, season_key
)

select
    s.*,
    extract(year from s.premiered_date)  as premiered_year,
    c.cast_size
from seasons as s
left join cast_sizes as c
    on c.show_name = s.show_name and c.season_key = s.season_key
