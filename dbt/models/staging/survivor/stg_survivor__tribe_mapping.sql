-- Which tribe each castaway was on, by episode, in US seasons.
-- Feeds bridge_team_membership.
with source as (
    select * from {{ source('survivor', 'tribe_mapping') }}
    where version = 'US'
),

renamed as (
    select
        version_season          as season_key,
        season                  as season_number,
        episode                 as episode_number,
        cast(day as integer)    as day,
        castaway_id,
        castaway                as castaway_short_name,
        tribe,
        tribe_status
    from source
)

select * from renamed
