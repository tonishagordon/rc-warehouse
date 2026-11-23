-- Tracker rows that can't be right. The failure says which row and why.
select source_file, 'Alliances' as sheet, source_row as excel_row, 'alliance has no name' as problem
from {{ ref('stg_manual__alliances') }} where alliance_name is null
union all
select source_file, 'Alliances', source_row, 'member left before joining'
from {{ ref('stg_manual__alliances') }} where episode_left < episode_joined
union all
select source_file, 'Alliances', source_row, 'episode is not a number'
from {{ ref('stg_manual__alliances') }}
where (episode_joined_raw is not null and episode_joined is null)
   or (episode_left_raw is not null and episode_left is null)
union all
select source_file, 'Votes', source_row, 'episode missing or not a number'
from {{ ref('stg_manual__votes') }} where episode is null
union all
select source_file, 'Votes', source_row, 'blindside must be Yes or No'
from {{ ref('stg_manual__votes') }} where blindside_raw is not null and is_blindside is null
union all
select source_file, 'Showmances', source_row, 'showmance ended before it started'
from {{ ref('stg_manual__showmances') }} where episode_ended < episode_started
union all
select source_file, 'Showmances', source_row, 'a showmance needs two different people'
from {{ ref('stg_manual__showmances') }} where player_1 = player_2
