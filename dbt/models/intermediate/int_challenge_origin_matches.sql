-- Cross-show entity resolution, step 1: link Challenge contestants to the
-- exact Survivor / Big Brother season they came from.
--
-- Blocking: the contestant's Original season ("Big Brother 20") narrows the
-- candidates to ~16-20 people, so matching only has to pick the right one
-- within that season.
-- Scoring: best of exact name, first+last, nickname+last, and Jaro-Winkler
-- similarity of normalized names.
-- Decision: auto-match when the best score is high AND clearly ahead of the
-- runner-up; send near-misses to review; the rest are no-match.
with challenge as (
    select * from {{ ref('int_person_mentions') }}
    where show_name = 'challenge' and origin_season_key is not null
),

candidates as (
    select * from {{ ref('int_person_mentions') }}
    where show_name in ('survivor', 'bigbrother')
),

scored as (
    select
        c.mention_key                       as challenge_mention_key,
        c.display_name                      as challenge_name,
        c.season_key                        as challenge_season_key,
        c.origin_season_key,
        m.mention_key                       as candidate_mention_key,
        m.display_name                      as candidate_name,
        m.source_person_id                  as candidate_source_person_id,
        greatest(
            case when c.name_norm = m.name_norm then 1.0 end,
            case when c.first_name_norm = m.first_name_norm
                  and c.last_name_norm  = m.last_name_norm then 0.98 end,
            case when c.last_name_norm = m.last_name_norm
                  and (c.nickname_norm  in (m.first_name_norm, m.nickname_norm)
                    or m.nickname_norm  in (c.first_name_norm, c.nickname_norm)) then 0.97 end,
            jaro_winkler_similarity(c.name_norm, m.name_norm)
        )                                   as score
    from challenge as c
    inner join candidates as m
        on m.season_key = c.origin_season_key
),

ranked as (
    select
        *,
        row_number() over (partition by challenge_mention_key order by score desc) as rnk,
        lead(score) over (partition by challenge_mention_key order by score desc)   as runner_up_score
    from scored
),

best as (
    select * from ranked where rnk = 1
)

select
    c.mention_key                                   as challenge_mention_key,
    c.display_name                                  as challenge_name,
    c.season_key                                    as challenge_season_key,
    c.origin_season_key,
    b.candidate_mention_key,
    b.candidate_name,
    b.candidate_source_person_id,
    round(b.score, 3)                               as score,
    round(b.score - coalesce(b.runner_up_score, 0), 3) as margin,
    case
        when b.candidate_mention_key is null            then 'no_candidates'
        when b.score >= 0.93 and b.score - coalesce(b.runner_up_score, 0) >= 0.05
                                                        then 'auto'
        when b.score >= 0.80                            then 'review'
        else 'no_match'
    end                                             as match_decision
from challenge as c
left join best as b
    on c.mention_key = b.challenge_mention_key
