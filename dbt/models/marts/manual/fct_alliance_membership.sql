-- Alliances recorded while watching: one row per member, linked to dim_person.
select
    a.show_name,
    a.season_key,
    a.alliance_name,
    a.member,
    c.person_id,
    a.episode_joined,
    a.episode_left,
    (a.episode_left is null)                     as still_together,
    a.notes
from {{ ref('stg_manual__alliances') }} as a
left join {{ ref('int_tracker_cast') }} as c
    on c.show_name = a.show_name and c.season_key = a.season_key and c.name = a.member
