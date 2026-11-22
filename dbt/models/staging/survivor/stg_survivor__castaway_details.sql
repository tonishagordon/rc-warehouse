-- One row per person (all versions). This feeds dim_person later.
-- Demographic columns (race, ethnicity, LGBT and BIPOC flags) are deliberately
-- not carried forward: see docs/decisions.md.
with source as (
    select * from {{ source('survivor', 'castaway_details') }}
),

renamed as (
    select
        castaway_id,
        full_name,
        full_name_detailed,
        castaway                        as castaway_short_name,
        last_name,
        cast(date_of_birth as date)     as date_of_birth,
        cast(date_of_death as date)     as date_of_death,
        gender,
        occupation
    from source
)

select * from renamed
