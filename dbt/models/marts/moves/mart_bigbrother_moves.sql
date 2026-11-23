-- One row per houseguest per US Big Brother season: Head of Household wins,
-- Veto wins, weeks on the block, and how their season ended. Counted from
-- the event rows of each season's voting table (one column = one eviction).

with events as (
    select season_key, col_index, event_type, value
    from {{ ref('stg_bigbrother__weekly_events') }}
    where event_type in ('hoh', 'veto_winner', 'nominations_initial', 'nominations_final')
),

labels as (
    select * from {{ ref('int_bigbrother_label_map') }}
),

hits as (
    -- a label "won" an event when it appears as a whole word in that cell
    select l.season_key, l.label, e.col_index, e.event_type
    from labels as l
    inner join events as e
        on e.season_key = l.season_key
       and contains({{ word_pad('e.value') }}, {{ word_pad('l.label') }})
),

counts as (
    select
        season_key,
        label,
        count(distinct col_index) filter (where event_type = 'hoh')                       as hoh_wins,
        count(distinct col_index) filter (where event_type = 'veto_winner')               as veto_wins,
        count(distinct col_index) filter (where event_type like 'nominations%')           as weeks_nominated
    from hits
    group by 1, 2
),

season_veto as (
    select season_key, bool_or(event_type = 'veto_winner') as season_has_veto
    from events group by 1
)

select
    l.season_key || '|' || l.label                                  as bigbrother_move_key,
    l.season_key,
    f.season_name,
    coalesce(sv.season_has_veto, false)                             as season_has_veto,
    l.label,
    l.houseguest_name,
    b.person_id,
    coalesce(c.hoh_wins, 0)                                         as hoh_wins,
    coalesce(c.veto_wins, 0)                                        as veto_wins,
    coalesce(c.hoh_wins, 0) + coalesce(c.veto_wins, 0)              as comp_wins,
    coalesce(c.weeks_nominated, 0)                                  as weeks_nominated,
    f.finish_percentile,
    f.made_final,
    f.is_winner
from labels as l
inner join {{ ref('bridge_person_mention') }} as b on b.mention_key = l.mention_key
inner join {{ ref('fct_appearance') }} as f
    on f.person_id = b.person_id and f.season_key = l.season_key and f.show_name = 'bigbrother'
left join counts as c on c.season_key = l.season_key and c.label = l.label
left join season_veto as sv on sv.season_key = l.season_key
