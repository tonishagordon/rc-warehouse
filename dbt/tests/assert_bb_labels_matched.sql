-- Every houseguest label in a voting table should map to one houseguest.
-- Warn (not fail): an unmatched label just drops that player from the
-- "Game moves" analysis, and the list shows which ones to fix.
{{ config(severity='warn') }}
select distinct g.season_key, g.row_label
from {{ ref('stg_bigbrother__voting_grid') }} as g
left join {{ ref('int_bigbrother_label_map') }} as m
    on m.season_key = g.season_key and m.label = g.row_label
where not g.is_event_row and g.row_label is not null and m.label is null
