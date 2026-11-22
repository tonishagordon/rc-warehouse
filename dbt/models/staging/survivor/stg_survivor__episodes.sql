-- One row per US Survivor episode.
with source as (
    select * from {{ source('survivor', 'episodes') }}
    where version = 'US'
),

renamed as (
    select
        version_season || '_E' || lpad(cast(episode as varchar), 2, '0')  as episode_key,
        version_season                          as season_key,
        season                                  as season_number,
        episode                                 as episode_number,
        cast(episode_number_overall as integer) as episode_number_overall,
        episode_title,
        episode_label,
        cast(episode_date as date)              as air_date,
        episode_length                          as episode_length_minutes,
        viewers                                 as viewers_millions,
        imdb_rating,
        cast(n_ratings as integer)              as imdb_n_ratings
    from source
)

select * from renamed
