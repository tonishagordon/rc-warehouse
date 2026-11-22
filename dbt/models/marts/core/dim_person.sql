-- One row per real person across Survivor, Big Brother, The Challenge and The Traitors.
with first_appearance as (
    -- each person's earliest appearance in the warehouse
    select
        b.person_id,
        b.show_name,
        case when b.show_name in ('challenge', 'traitors') then b.prior_shows_note end as origin_listed
    from {{ ref('bridge_person_mention') }} as b
    inner join {{ ref('dim_season') }} as s
        on s.show_name = b.show_name and s.season_key = b.season_key
    qualify row_number() over (
        partition by b.person_id order by s.premiered_date nulls last, b.season_key) = 1
),

background as (
    -- Where the person first became known: Survivor / Big Brother if they
    -- debuted there; otherwise the origin show their first cast table lists
    -- (The Real World, Are You the One?, Love Island...). Used by the app's
    -- Feeder Show Report and Strategist Penalty. (D015)
    select
        person_id,
        show_name                                                   as debut_show,
        case show_name
            when 'survivor'   then 'Survivor'
            when 'bigbrother' then 'Big Brother'
            else coalesce({{ origin_show('origin_listed') }}, 'Unknown')
        end                                                         as background
    from first_appearance
),

b as (
    select
        *,
        -- prefer the most official name: survivoR full name, then Wikipedia BB, then Challenge
        case show_name when 'survivor' then 1 when 'bigbrother' then 2 when 'traitors' then 3 else 4 end as name_priority
    from {{ ref('bridge_person_mention') }}
)

select
    person_id,
    first(display_name order by name_priority, length(display_name) desc)   as person_name,
    count(*)                                                                 as n_appearances,
    count(distinct show_name)                                                as n_shows,
    count(*) filter (where show_name = 'survivor')                           as survivor_seasons,
    count(*) filter (where show_name = 'bigbrother')                         as bigbrother_seasons,
    count(*) filter (where show_name = 'challenge')                          as challenge_seasons,
    count(*) filter (where show_name = 'traitors')                           as traitors_seasons,
    (count(distinct show_name) > 1)                                          as is_crossover,
    string_agg(distinct show_name, ', ' order by show_name)                  as shows,
    string_agg(distinct display_name, ' | ' order by display_name)           as name_variants,
    any_value(bg.debut_show)                                                 as debut_show,
    any_value(bg.background)                                                 as background
from b
left join background as bg using (person_id)
group by person_id
