-- One row per houseguest per voting column per target: what that houseguest
-- did that week. cell_status = 'vote' means target_label is who they voted
-- for (to EVICT in weekly columns; to WIN in the finale column = jury vote).
--
-- A cell counts as a vote only if its text matches houseguest row labels in
-- the same season: a single label ("Jason"), or two labels joined by " & " or
-- a space ("Alex & Amanda" in BB9's couples phase, "Drew Haley" in BB28's
-- two-target vote). Two-target cells become two rows. Anything else is a
-- status matched by pattern, or 'other' if unknown.
with grid as (
    select * from {{ ref('stg_bigbrother__voting_grid') }}
),

season_labels as (
    select distinct season_key, row_label as label
    from grid
    where not is_event_row
),

-- every text a vote cell can contain, mapped to the label(s) it names
vote_targets as (
    select season_key, label as match_text, label as target_label
    from season_labels

    union all

    select
        a.season_key,
        a.label || sep.s || b.label     as match_text,
        unnest([a.label, b.label])      as target_label
    from season_labels as a
    inner join season_labels as b
        on a.season_key = b.season_key
       and a.label <> b.label
    cross join (values (' & '), (' ')) as sep(s)
),

houseguest_cells as (
    select
        g.*,
        vt.target_label
    from grid as g
    left join vote_targets as vt
        on g.season_key = vt.season_key
       and g.value = vt.match_text
    where not g.is_event_row
      and g.value is not null
),

classified as (
    select
        season_key,
        season_number,
        row_label                       as voter_label,
        col_index,
        column_header,
        week_number,
        column_day,
        is_finale_column,
        value                           as cell_value,
        target_label,
        case
            when target_label is not null                       then 'vote'
            when value ilike '%head%of household%'
              or value ilike 'co-head%'                         then 'hoh'
            when value ilike 'nominated%'                       then 'nominated'
            when value ilike '%evicted%'                        then 'evicted'  -- incl. re-evicted, remained evicted
            when value ilike 'eliminated%'                      then 'eliminated'
            when value ilike 'expelled%'
              or value ilike 'removed%'                         then 'expelled'
            when value ilike 'walked%'
              or value ilike 'quit%'                            then 'walked'
            when value ilike 'exempt%'
              or value ilike '%not eligible%'
              or value ilike '%ineligible%'
              or value ilike 'no vote%'
              or value ilike 'abstain%'
              or value ilike '%void%'
              or value ilike 'saved%'
              or value ilike 'camp comeback%'
              or value ilike 'camp director%'
              or value ilike 'zombie%'
              or value ilike 'banished%'
              or value ilike 'non-houseguest%'
              or value ilike 'coach%'
              or value ilike 'backstage%'                       then 'no_vote'
            when value ilike 'coup d%'                          then 'power_used'  -- BB11 Coup d'État
            when value ilike '%offer%'                          then 'no_vote'     -- BB14 coaches' offer to join the game
            when value ilike 'winner%'                          then 'winner'
            when value ilike 'runner%'                          then 'runner_up'
            else 'other'
        end                             as cell_status
    from houseguest_cells
)

select
    season_key || '_' || lpad(cast(col_index as varchar), 2, '0') || '_' || voter_label
        || coalesce('_' || target_label, '')                                   as vote_key,
    *,
    count(target_label) over (
        partition by season_key, col_index, voter_label
    ) > 1                                                                       as is_multi_target,
    case when cell_status = 'vote'
         then case when is_finale_column then 'jury' else 'eviction' end end   as vote_type
from classified
