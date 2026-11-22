-- Warns (doesn't fail) for every Big Brother voting cell the parser couldn't
-- classify. Each returned row is a cell to look at; new twists show up here.
{{ config(severity='warn') }}

select season_key, voter_label, column_header, cell_value
from {{ ref('stg_bigbrother__votes') }}
where cell_status = 'other'
