-- Every event in an advantage's life (found, passed, played...) in US seasons.
-- Feeds ext_survivor_advantage.
with source as (
    select * from {{ source('survivor', 'advantage_movement') }}
    where version = 'US'
),

renamed as (
    select
        version_season              as season_key,
        season                      as season_number,
        advantage_id,
        sequence_id,
        castaway_id,
        castaway                    as castaway_short_name,
        cast(episode as integer)    as episode_number,
        cast(day as integer)        as day,
        event,
        played_for_id               as played_for_castaway_id,
        played_for                  as played_for_short_name,
        success,
        cast(votes_nullified as integer) as votes_nullified,
        cast(sog_id as integer)     as stage_of_game_id
    from source
)

select * from renamed
