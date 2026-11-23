-- Every name typed into a tracker must be in that season's cast.
-- The failure lists the file, sheet, Excel row and name to fix.
with names as (
    select source_file, 'Alliances' as sheet, source_row, show_name, season_key, member as name
    from {{ ref('stg_manual__alliances') }}
    union all
    select source_file, 'Votes', source_row, show_name, season_key, unnest([planned_target, voted_out, ran_the_vote])
    from {{ ref('stg_manual__votes') }}
    union all
    select source_file, 'Showmances', source_row, show_name, season_key, unnest([player_1, player_2])
    from {{ ref('stg_manual__showmances') }}
)
select n.source_file, n.sheet, n.source_row as excel_row, n.name as unknown_name
from names as n
left join {{ ref('int_tracker_cast') }} as c
    on c.show_name = n.show_name and c.season_key = n.season_key and c.name = n.name
where n.name is not null and c.name is null
