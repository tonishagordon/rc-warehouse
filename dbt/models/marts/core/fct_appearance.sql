-- One row per person per season, across all shows: the core fact table.
-- Career fields put every appearance in order across shows, so you can ask
-- "what was this person's first show?" or "how did Big Brother alums do in
-- their first Challenge?".
with base as (
    select
        b.person_id,
        b.show_name,
        b.season_key,
        b.display_name                       as name_as_billed,
        o.result_category,
        o.exit_method,
        o.game_role,
        o.result_raw,
        o.finish_place_final                 as finish_place,
        o.exit_day,
        s.season_name,
        s.series,
        s.premiered_date,
        s.premiered_year,
        s.cast_size
    from {{ ref('bridge_person_mention') }} as b
    inner join {{ ref('int_appearance_outcomes') }} as o
        on o.mention_key = b.mention_key
    inner join {{ ref('dim_season') }} as s
        on s.show_name = b.show_name and s.season_key = b.season_key
),

careers as (
    select
        *,
        row_number() over (
            partition by person_id order by premiered_date nulls last, season_key
        )                                                       as career_appearance_number,
        row_number() over (
            partition by person_id, show_name order by premiered_date nulls last, season_key
        )                                                       as show_appearance_number,
        first_value(show_name) over (
            partition by person_id order by premiered_date nulls last, season_key
        )                                                       as debut_show
    from base
)

select
    person_id || '|' || season_key                              as appearance_key,
    person_id,
    show_name,
    season_key,
    season_name,
    series,
    premiered_date,
    premiered_year,
    name_as_billed,
    result_category,
    exit_method,
    game_role,
    finish_place,
    cast_size,
    -- 1.0 = won, 0.0 = first out; comparable across shows of different sizes
    case when finish_place is not null and cast_size > 1
         then round(1 - (finish_place - 1) / (cast_size - 1), 3) end as finish_percentile,
    (result_category = 'winner')                                as is_winner,
    (result_category in ('winner', 'runner_up', 'finalist'))    as made_final,
    career_appearance_number,
    show_appearance_number,
    (show_appearance_number > 1)                                as is_returnee,
    debut_show,
    (show_name <> debut_show and show_appearance_number = 1)    as is_cross_show_debut,
    result_raw
from careers
