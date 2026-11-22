-- Every hand-entered crosswalk row must find exactly one mention on each side,
-- so a typo in seeds/crosswalk_manual.csv fails loudly instead of silently.
with seed as (
    select row_number() over () as row_num, * from {{ ref('crosswalk_manual') }}
),
m as (select * from {{ ref('int_person_mentions') }}),
counts as (
    select
        s.row_num, s.name_a, s.name_b,
        (select count(*) from m where m.show_name = s.show_a and m.season_key = s.season_a
            and m.name_norm = {{ normalize_name('s.name_a') }}) as a_matches,
        (select count(*) from m where m.show_name = s.show_b and m.season_key = s.season_b
            and m.name_norm = {{ normalize_name('s.name_b') }}) as b_matches
    from seed as s
)
select * from counts where a_matches <> 1 or b_matches <> 1
