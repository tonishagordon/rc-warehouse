-- One row per castaway per US season (an "appearance").
-- Some players can have more than one row in a season (e.g. re-entering the
-- game); the appearance_key uniqueness test is set to warn so we can see how often.
with source as (
    select * from {{ source('survivor', 'castaways') }}
    where version = 'US'
),

renamed as (
    select
        version_season || '_' || castaway_id    as appearance_key,
        version_season                          as season_key,
        season                                  as season_number,
        castaway_id,
        castaway                                as castaway_short_name,
        full_name,
        age                                     as age_at_filming,
        city,
        state,
        cast(place as integer)                  as finish_place,
        result,
        jury_status,
        original_tribe,
        jury                                    as is_juror,
        (finalist = 1)                          as is_finalist,
        (winner = 1)                            as is_winner,
        cast(episode as integer)                as exit_episode,
        cast(day as integer)                    as exit_day,
        cast("order" as integer)                as boot_order
    from source
)

select * from renamed
