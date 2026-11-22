-- Every source appearance with the person it belongs to.
-- This is how every fact table gets a person_id.
select
    'P' || substr(md5(c.cluster_root), 1, 10)  as person_id,
    m.mention_key,
    m.show_name,
    m.season_key,
    m.display_name,
    m.source_person_id,
    m.prior_shows_note
from {{ ref('int_person_clusters') }} as c
inner join {{ ref('int_person_mentions') }} as m
    on m.mention_key = c.mention_key
