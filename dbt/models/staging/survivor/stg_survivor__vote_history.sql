-- One row per vote cast at Tribal Council in US seasons
-- (voter -> target). Feeds fct_vote.
with source as (
    select * from {{ source('survivor', 'vote_history') }}
    where version = 'US'
),

renamed as (
    select
        version_season          as season_key,
        season                  as season_number,
        episode                 as episode_number,
        day,
        tribe_status,
        tribe,
        castaway_id             as voter_castaway_id,
        castaway                as voter_short_name,
        vote_id                 as target_castaway_id,
        vote                    as target_short_name,
        immunity,
        vote_event,
        vote_event_outcome,
        split_vote,
        (nullified = 1)         as is_nullified,
        (tie = 1)               as is_tie,
        voted_out_id            as voted_out_castaway_id,
        "order"                 as boot_order,
        vote_order,
        sog_id                  as stage_of_game_id,
        cast(challenge_id as integer) as challenge_id
    from source
)

select * from renamed
