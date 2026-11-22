-- Over-merge guard: a person shouldn't appear twice in the same season of the
-- same show. Warn (not error): some Challenge pages list a player in two tables.
{{ config(severity='warn') }}

select person_id, show_name, season_key, count(*) as mentions,
       string_agg(display_name, ' | ') as names
from {{ ref('bridge_person_mention') }}
group by person_id, show_name, season_key
having count(*) > 1
