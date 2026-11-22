-- Each show's own idea of "how did this person's season end", mapped onto
-- one shared vocabulary (D012):
--   result_category: winner / runner_up / finalist / eliminated / quit /
--                    removed / medical / in_progress / unknown
--   exit_method:     jury_vote / final_challenge / vote_out / eviction /
--                    banished / elimination_round / quit / removed / medical
-- plus a finish_place (1 = won) computed the same way for every show.
-- Grain: one row per mention (person x season x show).

with survivor as (
    select
        'survivor|' || c.appearance_key             as mention_key,
        c.season_key,
        c.finish_place,
        c.result                                    as result_raw,
        c.exit_day,
        c.exit_episode                              as exit_point,   -- episode
        case
            when c.is_winner                                        then 'winner'
            when c.result ilike 'runner-up' or c.result ilike 'runner up' then 'runner_up'
            when c.is_finalist                                      then 'finalist'
            when c.result is null and not s.is_season_complete      then 'in_progress'
            when c.result ilike '%quit%'                            then 'quit'
            when c.result ilike '%medic%' or c.result ilike '%evacuat%' then 'medical'
            when c.result ilike '%eject%' or c.result ilike '%removed%' then 'removed'
            when c.result is null                                   then 'unknown'
            else 'eliminated'
        end                                         as result_category,
        case
            when c.is_finalist                                      then 'jury_vote'
            when c.result ilike '%voted out%'                       then 'vote_out'
            when c.result ilike '%quit%'                            then 'quit'
            when c.result ilike '%medic%' or c.result ilike '%evacuat%' then 'medical'
            when c.result ilike '%eject%' or c.result ilike '%removed%' then 'removed'
            when c.result is not null                               then 'elimination_round'  -- fire-making, etc.
        end                                         as exit_method
    from {{ ref('stg_survivor__castaways') }} as c
    inner join {{ ref('stg_survivor__seasons') }} as s on s.season_key = c.season_key
),

-- Big Brother: a houseguest can have 2 result rows (e.g. evicted, then
-- returned and won). Keep the final one: best outcome, then latest exit.
bigbrother_rows as (
    select
        'bigbrother|' || season_key || '|' || houseguest_name as mention_key,
        season_key,
        result_raw,
        result_type,
        exit_day,
        row_number() over (
            partition by season_key, houseguest_name
            order by case result_type when 'winner' then 1 when 'runner_up' then 2
                                      when 'third_place' then 3 else 4 end,
                     exit_day desc nulls last
        ) as rn
    from {{ ref('stg_bigbrother__houseguests') }}
),

bigbrother as (
    select
        mention_key,
        season_key,
        cast(null as integer)                       as finish_place,
        result_raw,
        exit_day,
        exit_day                                    as exit_point,   -- day
        case result_type
            when 'winner'             then 'winner'
            when 'runner_up'          then 'runner_up'
            when 'third_place'        then 'finalist'
            when 'walked'             then 'quit'
            when 'expelled'           then 'removed'
            when 'eviction_nullified' then 'unknown'
            else 'eliminated'                                    -- evicted, banished, eliminated, exited
        end                                         as result_category,
        case result_type
            when 'winner'      then 'jury_vote'
            when 'runner_up'   then 'jury_vote'
            when 'third_place' then 'eviction'
            when 'evicted'     then 'eviction'
            when 'banished'    then 'banished'
            when 'eliminated'  then 'elimination_round'
            when 'exited'      then 'elimination_round'
            when 'walked'      then 'quit'
            when 'expelled'    then 'removed'
        end                                         as exit_method
    from bigbrother_rows
    where rn = 1
),

challenge as (
    select
        'challenge|' || contestant_key              as mention_key,
        season_key,
        cast(null as integer)                       as finish_place,
        finish_raw                                  as result_raw,
        cast(null as integer)                       as exit_day,
        exit_episode                                as exit_point,   -- episode
        case finish_type
            when 'winner'       then 'winner'
            when 'runner_up'    then 'runner_up'
            when 'third_place'  then 'finalist'
            when 'finalist'     then 'finalist'
            when 'eliminated'   then 'eliminated'
            when 'quit'         then 'quit'
            when 'medical'      then 'medical'
            when 'disqualified' then 'removed'
            when 'removed'      then 'removed'
            else 'unknown'
        end                                         as result_category,
        case finish_type
            when 'winner'       then 'final_challenge'
            when 'runner_up'    then 'final_challenge'
            when 'third_place'  then 'final_challenge'
            when 'finalist'     then 'final_challenge'
            when 'eliminated'   then 'elimination_round'
            when 'quit'         then 'quit'
            when 'medical'      then 'medical'
            when 'disqualified' then 'removed'
            when 'removed'      then 'removed'
        end                                         as exit_method
    from {{ ref('stg_challenge__contestants') }}
),

unioned as (
    select * from survivor
    union all select * from bigbrother
    union all select * from challenge
)

select
    *,
    -- One rule for every show: finalists by tier, then everyone else by how
    -- long they lasted. survivoR's own place is used when it exists.
    coalesce(
        finish_place,
        case when result_category in ('in_progress', 'unknown') then null else
        rank() over (
            partition by season_key
            order by case result_category when 'winner' then 1 when 'runner_up' then 2
                                          when 'finalist' then 3 else 4 end,
                     exit_point desc nulls last
        ) end
    )                                               as finish_place_final
from unioned
