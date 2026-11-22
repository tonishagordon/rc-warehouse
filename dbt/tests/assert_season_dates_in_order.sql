-- Within a show, a later season number should not premiere before an earlier
-- one. Catches date-parsing mistakes (e.g. a stray date read as a premiere).
-- Only the main numbered series are compared; spin-offs run in parallel.
{{ config(severity='warn') }}

with s as (
    select show_name, series, season_key, season_number, premiered_date,
           lag(premiered_date) over (partition by show_name, series order by season_number) as prev_premiere,
           lag(season_key)     over (partition by show_name, series order by season_number) as prev_season
    from {{ ref('dim_season') }}
    where series in ('Survivor', 'Big Brother', 'The Challenge')
)
select * from s
where premiered_date < prev_premiere
