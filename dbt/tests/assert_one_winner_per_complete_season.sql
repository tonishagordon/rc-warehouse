-- Every finished season should have at least one winner in fct_appearance.
-- Warn: some Challenge seasons crown pairs/teams (several winners), and a
-- missing winner usually means unrecognized Finish text upstream.
{{ config(severity='warn') }}

select s.show_name, s.season_key, s.season_name
from {{ ref('dim_season') }} as s
left join {{ ref('fct_appearance') }} as f
    on f.season_key = s.season_key and f.is_winner
where s.is_season_complete
group by 1, 2, 3
having count(f.person_id) = 0
