-- What each advantage was (Hidden Immunity Idol, Extra Vote, Shot in the
-- Dark...) for US seasons. Joins to advantage_movement on advantage_id.
select
    version_season          as season_key,
    season                  as season_number,
    advantage_id,
    advantage_type,
    clue_details,
    location_found,
    conditions
from {{ source('survivor', 'advantage_details') }}
where version = 'US'
