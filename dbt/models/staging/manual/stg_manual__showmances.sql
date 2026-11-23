-- One row per Big Brother showmance.
select
    show_name,
    season_key,
    source_file,
    cast(source_row as integer)                  as source_row,
    trim(player_1)                               as player_1,
    trim(player_2)                               as player_2,
    try_cast(episode_started as double)::integer as episode_started,
    try_cast(episode_ended as double)::integer   as episode_ended,
    episode_started                              as episode_started_raw,
    episode_ended                                as episode_ended_raw,
    notes
from {{ source('manual', 'showmances') }}
