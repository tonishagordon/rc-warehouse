-- Every hand-entered outcome correction must match exactly one appearance,
-- so a typo in seeds/outcome_overrides.csv can't silently do nothing.
with ov as (select * from {{ ref('outcome_overrides') }}),
hits as (
    select ov.show_name, ov.season_key, ov.name_as_billed, count(b.mention_key) as matches
    from ov
    left join {{ ref('bridge_person_mention') }} as b
        on b.show_name = ov.show_name
       and b.season_key = ov.season_key
       and lower(b.display_name) = lower(ov.name_as_billed)
    group by 1, 2, 3
)
select * from hits where matches <> 1
