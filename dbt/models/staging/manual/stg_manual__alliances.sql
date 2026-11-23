-- One row per alliance member, as entered in the tracker.
select
    show_name,
    season_key,
    source_file,
    cast(source_row as integer)                 as source_row,
    trim(alliance_name)                         as alliance_name,
    trim(member)                                as member,
    try_cast(episode_joined as double)::integer as episode_joined,
    try_cast(episode_left as double)::integer   as episode_left,
    episode_joined                              as episode_joined_raw,
    episode_left                                as episode_left_raw,
    notes
from {{ source('manual', 'alliances') }}
