-- Over-merge guard: one person can't be two different survivoR castaways.
-- If this fails, a name rule glued two different people together.
select b.person_id, count(distinct b.source_person_id) as castaway_ids
from {{ ref('bridge_person_mention') }} as b
where b.show_name = 'survivor'
group by b.person_id
having count(distinct b.source_person_id) > 1
