-- Feature table for the Challenge "return ticket" model (D016).
-- One row per Challenge ROOKIE season: what we know when their first season
-- ends, and whether they were ever cast again (the label).
--
-- label_known = debut through 2023, so everyone has had time to be re-cast.
-- Later rookies are scored by the model instead ("will they be back?").
with rookies as (
    select f.*, p.background, p.challenge_seasons
    from {{ ref('fct_appearance') }} as f
    inner join {{ ref('dim_person') }} as p using (person_id)
    where f.show_name = 'challenge'
      and f.show_appearance_number = 1
)

select
    person_id,
    season_key,
    season_name,
    premiered_year,
    name_as_billed,
    background,
    case
        when background in ('The Real World', 'Road Rules', 'The Challenge') then 'mtv_original'
        when background in ('Survivor', 'Big Brother')                        then 'survivor_bb'
        when background in ('Are You the One?', 'Love Island',
                            'Ex on the Beach', 'Too Hot to Handle')           then 'dating_show'
        else 'other'
    end                                                     as background_group,
    finish_percentile,
    cast(is_winner as integer)                              as won_first_season,
    cast(made_final as integer)                             as made_final_first_season,
    cast(exit_method in ('quit', 'removed', 'medical') as integer) as left_early_by_choice_or_rule,
    cast_size,
    (premiered_year <= 2023)                                as label_known,
    case when premiered_year <= 2023
         then cast(challenge_seasons > 1 as integer) end    as returned
from rookies
where finish_percentile is not null
