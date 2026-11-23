-- Guard against silent zeroes: if survivoR renames its event values or the
-- Big Brother event rows stop matching, these totals drop to 0 and the
-- "Game moves" page would quietly report nonsense. Fail instead.
select 'survivor idols found' as check_name, sum(idols_found) as total
from {{ ref('mart_survivor_moves') }}
having coalesce(sum(idols_found), 0) = 0
union all
select 'survivor idol plays', sum(idol_plays)
from {{ ref('mart_survivor_moves') }}
having coalesce(sum(idol_plays), 0) = 0
union all
select 'big brother veto wins', sum(veto_wins)
from {{ ref('mart_bigbrother_moves') }}
having coalesce(sum(veto_wins), 0) = 0
union all
select 'big brother hoh wins', sum(hoh_wins)
from {{ ref('mart_bigbrother_moves') }}
having coalesce(sum(hoh_wins), 0) = 0
