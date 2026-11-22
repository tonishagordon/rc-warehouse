-- One row per Traitors (US) season.
select distinct
    season_key,
    cast(substr(season_key, 3) as integer)                          as season_number,
    'The Traitors season ' || cast(cast(substr(season_key, 3) as integer) as varchar) as season_name
from {{ source('traitors', 'wiki_tables') }}
