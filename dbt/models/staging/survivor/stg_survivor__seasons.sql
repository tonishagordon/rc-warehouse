-- One row per US Survivor season.
with source as (
    select * from {{ source('survivor', 'season_summary') }}
    where version = 'US'
),

renamed as (
    select
        version_season                      as season_key,
        season                              as season_number,
        season_name,
        location,
        country,
        tribe_setup,
        n_cast,
        n_tribes,
        cast(n_finalists as integer)        as n_finalists,
        n_jury,
        winner_id                           as winner_castaway_id,
        winner                              as winner_name,
        final_vote,
        cast(premiered as date)             as premiered_date,
        cast(ended as date)                 as ended_date,
        cast(filming_started as date)       as filming_started_date,
        cast(filming_ended as date)         as filming_ended_date,
        viewers_premiere,
        viewers_finale,
        viewers_mean,
        (winner_id is not null)             as is_season_complete
    from source
)

select * from renamed
