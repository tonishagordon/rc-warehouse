-- One row per castaway exit in US seasons.
with source as (
    select * from {{ source('survivor', 'boot_order') }}
    where version = 'US'
),

renamed as (
    select
        version_season          as season_key,
        season                  as season_number,
        castaway_id,
        castaway                as castaway_short_name,
        episode                 as episode_number,
        day,
        "order"                 as boot_order,
        result
    from source
)

select * from renamed
