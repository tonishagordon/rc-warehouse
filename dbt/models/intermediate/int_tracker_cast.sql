-- The names a tracker may use, per season, linked to the person they mean.
-- Same lists ingest/make_tracker.py puts in each tracker's Cast tab.
select
    'survivor'                                   as show_name,
    c.season_key,
    c.castaway_short_name                        as name,
    b.person_id
from {{ ref('stg_survivor__castaways') }} as c
left join {{ ref('bridge_person_mention') }} as b
    on b.mention_key = 'survivor|' || c.appearance_key
group by all

union all

select
    'bigbrother',
    m.season_key,
    m.label,
    b.person_id
from {{ ref('int_bigbrother_label_map') }} as m
left join {{ ref('bridge_person_mention') }} as b on b.mention_key = m.mention_key
