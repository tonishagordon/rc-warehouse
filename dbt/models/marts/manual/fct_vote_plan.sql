-- The plan at each Tribal Council / eviction vs. what happened, recorded
-- while watching. A "plan failed" row is one where the planned target
-- stayed and someone else went home.
select
    v.show_name,
    v.season_key,
    v.episode,
    v.planned_target,
    pt.person_id                                 as planned_target_person_id,
    v.voted_out,
    vo.person_id                                 as voted_out_person_id,
    v.is_blindside,
    (v.planned_target is not null and v.voted_out is not null
        and v.planned_target <> v.voted_out)     as plan_failed,
    v.ran_the_vote,
    rv.person_id                                 as ran_the_vote_person_id,
    v.notes
from {{ ref('stg_manual__votes') }} as v
left join {{ ref('int_tracker_cast') }} as pt
    on pt.show_name = v.show_name and pt.season_key = v.season_key and pt.name = v.planned_target
left join {{ ref('int_tracker_cast') }} as vo
    on vo.show_name = v.show_name and vo.season_key = v.season_key and vo.name = v.voted_out
left join {{ ref('int_tracker_cast') }} as rv
    on rv.show_name = v.show_name and rv.season_key = v.season_key and rv.name = v.ran_the_vote
