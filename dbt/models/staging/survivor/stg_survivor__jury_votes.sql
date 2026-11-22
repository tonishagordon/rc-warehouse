-- One row per juror x finalist in US seasons; vote = 1 if the juror voted for them.
-- In-progress seasons have juror rows before the final vote happens (no finalist
-- yet). Those placeholder rows are excluded: see docs/decisions.md D004.
with source as (
    select * from {{ source('survivor', 'jury_votes') }}
    where version = 'US'
      and finalist_id is not null
),

renamed as (
    select
        version_season          as season_key,
        season                  as season_number,
        castaway_id             as juror_castaway_id,
        castaway                as juror_short_name,
        finalist_id             as finalist_castaway_id,
        finalist                as finalist_short_name,
        (vote = 1)              as voted_for_finalist
    from source
)

select * from renamed
