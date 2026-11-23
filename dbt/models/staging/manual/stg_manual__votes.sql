-- One row per Tribal Council / eviction: the plan vs. what happened.
select
    show_name,
    season_key,
    source_file,
    cast(source_row as integer)                 as source_row,
    try_cast(episode as double)::integer        as episode,
    episode                                     as episode_raw,
    trim(planned_target)                        as planned_target,
    trim(voted_out)                             as voted_out,
    case lower(trim(blindside)) when 'yes' then true when 'no' then false end as is_blindside,
    blindside                                   as blindside_raw,
    trim(ran_the_vote)                          as ran_the_vote,
    notes
from {{ source('manual', 'votes') }}
