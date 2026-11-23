-- Every completed Survivor season from 35 on had exactly one fire-making
-- loser at the final four. Warn if the fire-making rule finds 0 or 2+.
{{ config(severity='warn') }}
select f.season_key, f.season_name, count(*) filter (where f.exit_method = 'fire_making') as fire_making_losers
from {{ ref('fct_appearance') }} as f
inner join {{ ref('stg_survivor__seasons') }} as s on s.season_key = f.season_key
where f.show_name = 'survivor' and s.is_season_complete
  and cast(regexp_extract(f.season_key, '(\d+)', 1) as integer) >= 35
group by 1, 2
having count(*) filter (where f.exit_method = 'fire_making') <> 1
