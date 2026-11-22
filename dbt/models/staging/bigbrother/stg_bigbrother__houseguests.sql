-- One row per houseguest per US Big Brother season, rebuilt from the
-- cell-level raw data (the "HouseGuests" table on each season's page).
with houseguest_tables as (
    -- first table under the "HouseGuests" heading in each season
    select season_key, min(table_index) as table_index
    from {{ source('bigbrother', 'wiki_tables') }}
    where section = 'HouseGuests'
    group by season_key
),

cells as (
    select c.season_key, c.row_index, c.column_header, c.value
    from {{ source('bigbrother', 'wiki_cells') }} as c
    inner join houseguest_tables as t
        on c.season_key = t.season_key
       and c.table_index = t.table_index
),

pivoted as (
    select
        season_key,
        row_index,
        max(case when column_header ilike 'name%'        then value end) as houseguest_name,
        max(case when column_header ilike 'age%'         then value end) as age_raw,
        max(case when column_header ilike 'occupation%'  then value end) as occupation,
        max(case when column_header ilike 'residence%'
                   or column_header ilike 'hometown%'    then value end) as residence,
        max(case when column_header ilike 'result%'
                   or column_header ilike 'status%'      then value end) as result_raw
    from cells
    group by season_key, row_index
),

-- Returning players carry their earlier seasons in the Name cell, e.g.
-- "Rachel Reilly Big Brother 12 & Big Brother 13". Split that off: the name
-- part is used for matching, the note is a free signal for entity resolution.
name_split as (
    select
        * exclude (houseguest_name),
        houseguest_name as name_raw,
        regexp_extract(
            houseguest_name,
            '^(.*?)\s+((Big Brother|Celebrity Big Brother|Survivor|The Amazing Race|The Challenge|Love Island|The Traitors).*)$',
            ['clean_name', 'prior_shows_note']
        ) as parts
    from pivoted
    where houseguest_name is not null
)

select
    season_key || '_' || lpad(cast(row_index as varchar), 2, '0')   as houseguest_key,
    season_key,
    cast(substr(season_key, 3) as integer)                           as season_number,
    row_index                                                        as table_row,
    coalesce(nullif(parts.clean_name, ''), name_raw)                 as houseguest_name,
    name_raw                                                         as houseguest_name_raw,
    nullif(parts.prior_shows_note, '')                               as prior_shows_note,
    try_cast(regexp_extract(age_raw, '(\d+)', 1) as integer)         as age_at_filming,
    occupation,
    residence,
    result_raw,
    case
        when result_raw ilike 'winner%'                               then 'winner'
        when result_raw ilike 'runner%'                               then 'runner_up'
        when result_raw ilike 'third place%'                          then 'third_place'
        when result_raw ilike '%nullified%'                           then 'eviction_nullified'
        when result_raw ilike '%expelled%'
          or result_raw ilike '%removed%'                             then 'expelled'
        when result_raw ilike '%walked%'
          or result_raw ilike '%quit%'
          or result_raw ilike '%left%'                                then 'walked'
        when result_raw ilike '%banished%'                            then 'banished'
        when result_raw ilike '%eliminated%'                          then 'eliminated'
        when result_raw ilike '%exited%'                              then 'exited'
        when result_raw ilike '%evicted%'                             then 'evicted'
    end                                                              as result_type,
    try_cast(regexp_extract(result_raw, 'Day (\d+)', 1) as integer)  as exit_day
from name_split
