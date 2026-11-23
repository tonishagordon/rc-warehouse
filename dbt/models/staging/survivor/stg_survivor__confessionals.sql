-- Confessionals per castaway per episode in US seasons: how much screen
-- time "in the interview chair" each player got. index_count is survivoR's
-- standardized measure (confessionals relative to what's expected given how
-- many players were left), so it compares fairly across seasons.
with source as (
    select * from {{ source('survivor', 'confessionals') }}
    where version = 'US'
)

select
    version_season          as season_key,
    season                  as season_number,
    episode                 as episode_number,
    castaway_id,
    castaway                as castaway_short_name,
    confessional_count,
    confessional_time       as confessional_seconds,
    index_count             as confessional_index
from source
