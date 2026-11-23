-- Feature table for the "Who wins Survivor?" model (D016).
-- One row per castaway who reached the MERGE, using only what happened
-- before the merge episode: their pre-merge game and their pre-merge edit.
-- Completed seasons carry labels (won / made the final); the season still
-- airing is scored live, among the players still in the game.
with merge_episode as (
    select season_key, min(episode_number) as merge_episode
    from {{ ref('stg_survivor__tribe_mapping') }}
    where tribe_status in ('Merged', 'Mergatory')
    group by season_key
),

at_merge as (
    select distinct t.season_key, t.castaway_id, m.merge_episode
    from {{ ref('stg_survivor__tribe_mapping') }} as t
    inner join merge_episode as m
        on m.season_key = t.season_key and t.episode_number = m.merge_episode
    where t.tribe_status in ('Merged', 'Mergatory')
),

votes_against as (
    select v.season_key, v.target_castaway_id as castaway_id, count(*) as pre_votes_against
    from {{ ref('stg_survivor__vote_history') }} as v
    inner join merge_episode as m using (season_key)
    where v.episode_number < m.merge_episode and v.target_castaway_id is not null
    group by 1, 2
),

voting as (
    select
        v.season_key,
        v.voter_castaway_id as castaway_id,
        count(distinct v.episode_number) as pre_tribals_attended,
        avg(case when v.target_castaway_id = v.voted_out_castaway_id then 1.0 else 0.0 end)
            filter (where v.voted_out_castaway_id is not null) as pre_majority_vote_rate
    from {{ ref('stg_survivor__vote_history') }} as v
    inner join merge_episode as m using (season_key)
    where v.episode_number < m.merge_episode
    group by 1, 2
),

challenges as (
    select c.season_key, c.castaway_id,
           avg(case when c.won then 1.0 else 0.0 end) as pre_challenge_win_rate
    from {{ ref('stg_survivor__challenge_results') }} as c
    inner join merge_episode as m using (season_key)
    where c.episode_number < m.merge_episode and not coalesce(c.sat_out, false)
    group by 1, 2
),

edit as (
    select c.season_key, c.castaway_id,
           sum(c.confessional_count)  as pre_confessionals,
           avg(c.confessional_index)  as pre_confessional_index
    from {{ ref('stg_survivor__confessionals') }} as c
    inner join merge_episode as m using (season_key)
    where c.episode_number < m.merge_episode
    group by 1, 2
),

advantages as (
    select a.season_key, a.castaway_id, count(*) as pre_advantages_found
    from {{ ref('stg_survivor__advantage_movement') }} as a
    inner join merge_episode as m using (season_key)
    where a.episode_number < m.merge_episode and a.event ilike 'found%'
    group by 1, 2
),

appearances as (
    select
        c.*,
        count(*) over (partition by c.castaway_id order by c.season_number
                       rows between unbounded preceding and 1 preceding) as prior_seasons
    from {{ ref('stg_survivor__castaways') }} as c
),

seasons as (
    select season_key, season_name, is_season_complete from {{ ref('stg_survivor__seasons') }}
)

select
    am.season_key || '_' || am.castaway_id                      as merge_player_key,
    am.season_key,
    s.season_name,
    ap.season_number,
    am.castaway_id,
    ap.full_name,
    ap.castaway_short_name,
    count(*) over (partition by am.season_key)                  as merge_size,
    ap.age_at_filming,
    coalesce(ap.prior_seasons, 0)                               as prior_seasons,
    coalesce(va.pre_votes_against, 0)                           as pre_votes_against,
    coalesce(vo.pre_tribals_attended, 0)                        as pre_tribals_attended,
    coalesce(vo.pre_majority_vote_rate, 0.5)                    as pre_majority_vote_rate,
    coalesce(ch.pre_challenge_win_rate, 0.5)                    as pre_challenge_win_rate,
    coalesce(ed.pre_confessionals, 0)                           as pre_confessionals,
    coalesce(ed.pre_confessional_index, 0)                      as pre_confessional_index,
    coalesce(ad.pre_advantages_found, 0)                        as pre_advantages_found,
    s.is_season_complete,
    -- labels (completed seasons only)
    case when s.is_season_complete then cast(coalesce(ap.is_winner, false) as integer) end   as won,
    case when s.is_season_complete then cast(coalesce(ap.is_finalist, false) as integer) end as made_final,
    -- for the live season: still playing right now?
    (not s.is_season_complete and ap.result is null)            as still_in_game
from at_merge as am
inner join appearances as ap
    on ap.season_key = am.season_key and ap.castaway_id = am.castaway_id
inner join seasons as s on s.season_key = am.season_key
left join votes_against as va on va.season_key = am.season_key and va.castaway_id = am.castaway_id
left join voting as vo        on vo.season_key = am.season_key and vo.castaway_id = am.castaway_id
left join challenges as ch    on ch.season_key = am.season_key and ch.castaway_id = am.castaway_id
left join edit as ed          on ed.season_key = am.season_key and ed.castaway_id = am.castaway_id
left join advantages as ad    on ad.season_key = am.season_key and ad.castaway_id = am.castaway_id
