-- The Traitors season 5 cast (announced Sept 2026, airs 2027), linked to
-- dim_person where the player has a track record in this warehouse.
-- Matching reuses normalize_name(), restricted to the show the cast note
-- names, and also accepts "goes by" names (survivoR short name + surname,
-- e.g. "Q Burdette").
with cast_list as (
    select
        name,
        known_for,
        nullif(warehouse_show, '')          as warehouse_show,
        {{ normalize_name('name') }}        as name_norm
    from {{ ref('traitors_s5_cast') }}
),

mentions as (
    select b.person_id, m.show_name, m.name_norm, m.nickname_norm, m.last_name_norm
    from {{ ref('int_person_mentions') }} as m
    inner join {{ ref('bridge_person_mention') }} as b using (mention_key)
),

matched as (
    select distinct c.name, m.person_id
    from cast_list as c
    inner join mentions as m
        on m.show_name = c.warehouse_show
       and (m.name_norm = c.name_norm
            or m.nickname_norm || ' ' || m.last_name_norm = c.name_norm)
)

select
    c.name,
    c.known_for,
    c.warehouse_show,
    m.person_id,
    (m.person_id is not null) as has_track_record
from cast_list as c
left join matched as m using (name)
