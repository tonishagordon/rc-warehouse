-- One row per real person across Survivor, Big Brother and The Challenge.
with b as (
    select
        *,
        -- prefer the most official name: survivoR full name, then Wikipedia BB, then Challenge
        case show_name when 'survivor' then 1 when 'bigbrother' then 2 else 3 end as name_priority
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
    (count(distinct show_name) > 1)                                          as is_crossover,
    string_agg(distinct show_name, ', ' order by show_name)                  as shows,
    string_agg(distinct display_name, ' | ' order by display_name)           as name_variants
from b
group by person_id
