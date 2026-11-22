-- One row per castaway per challenge in US seasons.
with source as (
    select * from {{ source('survivor', 'challenge_results') }}
    where version = 'US'
),

renamed as (
    select
        version_season                  as season_key,
        season                          as season_number,
        episode                         as episode_number,
        challenge_id,
        castaway_id,
        castaway                        as castaway_short_name,
        tribe,
        tribe_status,
        team,
        challenge_type,
        outcome_type,
        result,
        result_notes,
        chosen_for_reward,
        (sit_out = 1)                   as sat_out,
        cast(order_of_finish as integer) as order_of_finish,
        (won = 1)                       as won,
        (won_tribal_reward = 1)         as won_tribal_reward,
        (won_tribal_immunity = 1)       as won_tribal_immunity,
        (won_team_reward = 1)           as won_team_reward,
        (won_team_immunity = 1)         as won_team_immunity,
        (won_individual_reward = 1)     as won_individual_reward,
        (won_individual_immunity = 1)   as won_individual_immunity,
        (won_duel = 1)                  as won_duel,
        sog_id                          as stage_of_game_id
    from source
)

select * from renamed
