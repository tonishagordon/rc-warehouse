-- One row per castaway per US Survivor season: idols and advantages, how
-- they voted, votes against them, challenge wins, days lasted, and how their
-- season ended. Feeds the "Game moves" page.
with details as (
    select season_key, advantage_id, advantage_type
    from {{ ref('stg_survivor__advantage_details') }}
),

moves as (
    select
        m.*,
        coalesce(d.advantage_type, 'Unknown')                           as advantage_type,
        coalesce(d.advantage_type ilike '%idol%'
                 and d.advantage_type not ilike '%nullifier%', false)   as is_idol
    from {{ ref('stg_survivor__advantage_movement') }} as m
    left join details as d using (season_key, advantage_id)
),

advantages as (
    select
        season_key,
        castaway_id,
        count(distinct advantage_id) filter (where event ilike 'found%' or event ilike 'received%')   as advantages_held,
        count(distinct advantage_id) filter (where is_idol and (event ilike 'found%' or event ilike 'received%')) as idols_held,
        count(distinct advantage_id) filter (where is_idol and event ilike 'found%')                 as idols_found,
        count(*) filter (where is_idol and event ilike 'played%')                                     as idol_plays,
        count(*) filter (where is_idol and event ilike 'played%' and coalesce(votes_nullified, 0) > 0) as idol_plays_cancelling_votes,
        count(*) filter (where is_idol and event ilike 'played%'
                         and played_for_castaway_id is not null
                         and played_for_castaway_id <> castaway_id)                                    as idol_plays_for_others,
        coalesce(sum(votes_nullified) filter (where is_idol and event ilike 'played%'), 0)             as votes_cancelled,
        bool_or(is_idol and event ilike '%voted out%')                                                 as voted_out_holding_idol
    from moves
    group by 1, 2
),

votes as (
    select
        season_key,
        voter_castaway_id                                                         as castaway_id,
        count(*) filter (where target_castaway_id is not null)                    as votes_cast,
        count(*) filter (where target_castaway_id = voted_out_castaway_id)        as votes_with_the_boot
    from {{ ref('stg_survivor__vote_history') }}
    where voter_castaway_id is not null
    group by 1, 2
),

votes_against as (
    select season_key, target_castaway_id as castaway_id, count(*) as votes_against
    from {{ ref('stg_survivor__vote_history') }}
    where target_castaway_id is not null
    group by 1, 2
),

challenges as (
    select
        season_key,
        castaway_id,
        count(*) filter (where won_individual_immunity)     as individual_immunity_wins,
        count(*) filter (where won_individual_reward)       as individual_reward_wins,
        count(*) filter (where won_tribal_immunity or won_team_immunity) as tribe_immunity_wins
    from {{ ref('stg_survivor__challenge_results') }}
    group by 1, 2
),

days as (
    -- last day in the game (a player who re-entered has two rows: take the later one)
    select season_key, castaway_id, max(exit_day) as days_lasted
    from {{ ref('stg_survivor__castaways') }}
    group by 1, 2
),

season_idols as (
    select season_key, count(*) > 0 as season_has_idols
    from moves where is_idol group by 1
),

players as (
    select distinct
        b.person_id,
        b.season_key,
        regexp_extract(b.mention_key, '^survivor\|[^_]+_(.+)$', 1)                as castaway_id
    from {{ ref('bridge_person_mention') }} as b
    where b.show_name = 'survivor'
)

select
    p.season_key || '_' || p.castaway_id                                          as survivor_move_key,
    p.season_key,
    f.season_name,
    s.is_season_complete,
    coalesce(si.season_has_idols, false)                                          as season_has_idols,
    p.castaway_id,
    p.person_id,
    f.name_as_billed                                                              as player_name,
    coalesce(a.advantages_held, 0)                                                as advantages_held,
    coalesce(a.idols_held, 0)                                                     as idols_held,
    coalesce(a.idols_found, 0)                                                    as idols_found,
    coalesce(a.idol_plays, 0)                                                     as idol_plays,
    coalesce(a.idol_plays_cancelling_votes, 0)                                    as idol_plays_cancelling_votes,
    coalesce(a.idol_plays_for_others, 0)                                          as idol_plays_for_others,
    coalesce(a.votes_cancelled, 0)                                                as votes_cancelled,
    coalesce(a.voted_out_holding_idol, false)                                     as voted_out_holding_idol,
    coalesce(v.votes_cast, 0)                                                     as votes_cast,
    coalesce(v.votes_with_the_boot, 0)                                            as votes_with_the_boot,
    case when v.votes_cast > 0 then round(v.votes_with_the_boot / v.votes_cast, 3) end as majority_vote_rate,
    coalesce(va.votes_against, 0)                                                 as votes_against,
    coalesce(ch.individual_immunity_wins, 0)                                      as individual_immunity_wins,
    coalesce(ch.individual_reward_wins, 0)                                        as individual_reward_wins,
    coalesce(ch.tribe_immunity_wins, 0)                                           as tribe_immunity_wins,
    d.days_lasted,
    f.finish_percentile,
    f.made_final,
    f.is_winner
from players as p
inner join {{ ref('fct_appearance') }} as f
    on f.person_id = p.person_id and f.season_key = p.season_key and f.show_name = 'survivor'
inner join {{ ref('stg_survivor__seasons') }} as s on s.season_key = p.season_key
left join advantages as a   on a.season_key = p.season_key and a.castaway_id = p.castaway_id
left join votes as v        on v.season_key = p.season_key and v.castaway_id = p.castaway_id
left join season_idols as si on si.season_key = p.season_key
left join votes_against as va on va.season_key = p.season_key and va.castaway_id = p.castaway_id
left join challenges as ch    on ch.season_key = p.season_key and ch.castaway_id = p.castaway_id
left join days as d           on d.season_key = p.season_key and d.castaway_id = p.castaway_id
