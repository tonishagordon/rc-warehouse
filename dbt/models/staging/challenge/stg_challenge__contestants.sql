-- One row per contestant per Challenge season, from the "Contestants" (or,
-- in the earliest seasons, "Cast") tables on each season page.
--
-- Layouts vary: separate Male/Female tables, Male partner + Female partner
-- in one row, or a single cast list. Any column whose header names a person
-- (contestant / partner / cast / name / player) becomes a contestant row;
-- the row's Original season and Finish apply to everyone named in it.
with seasons as (
    select season_key from {{ ref('stg_challenge__seasons') }}
),

tables as (
    select t.*
    from {{ source('challenge', 'wiki_tables') }} as t
    inner join seasons as s on t.season_key = s.season_key
),

-- Normal case: tables under a "Contestants" or "Cast" heading.
by_section as (
    select season_key, table_index
    from tables
    where section ilike 'contestants' or section ilike 'cast'
),

-- Some seasons put the cast under sub-headings instead (e.g. Veterans /
-- Rookies on Fresh Meat, Champions / Challengers on The Ruins). For seasons
-- with no Contestants/Cast section, use any table with an "Original season"
-- column. See docs/decisions.md D007.
by_header as (
    select season_key, table_index
    from tables
    where headers ilike '%original%'
      and season_key not in (select season_key from by_section)
),

contestant_tables as (
    select * from by_section
    union
    select * from by_header
),

cells as (
    select c.season_key, c.table_index, c.row_index, c.col_index, c.column_header, c.value
    from {{ source('challenge', 'wiki_cells') }} as c
    inner join contestant_tables as t
        on c.season_key = t.season_key
       and c.table_index = t.table_index
),

row_attributes as (
    select
        season_key, table_index, row_index,
        max(case when column_header ilike '%original%'
                   or column_header ilike '%known for%'           then value end) as original_season,
        max(case when column_header ilike '%finish%'
                   or column_header ilike 'result%'               then value end) as finish_raw
    from cells
    group by season_key, table_index, row_index
),

names as (
    select season_key, table_index, row_index, col_index, column_header, value as contestant_name
    from cells
    where regexp_matches(lower(column_header),
              'contestant|partner|^cast|^name|player|mercenar|veteran|rookie|relative|famil|challenger|champion|member|pro')
      and not regexp_matches(lower(column_header), 'original|known for|finish|result|episode')
      and value is not null
      and value <> column_header            -- repeated header rows
)

select
    n.season_key || '_' || n.table_index || '_' || lpad(cast(n.row_index as varchar), 2, '0')
        || '_' || n.col_index                                         as contestant_key,
    n.season_key,
    n.contestant_name,
    case
        when n.column_header ilike 'female%' then 'Female'
        when n.column_header ilike 'male%'   then 'Male'
    end                                                               as gender_from_table,
    (n.column_header ilike '%mercenar%')                              as is_mercenary,
    a.original_season,
    case
        when a.original_season ilike '%real world%'          then 'The Real World'
        when a.original_season ilike '%road rules%'          then 'Road Rules'
        when a.original_season ilike '%fresh meat%'          then 'The Challenge: Fresh Meat'
        when a.original_season ilike '%are you the one%'     then 'Are You the One?'
        when a.original_season ilike '%ex on the beach%'     then 'Ex on the Beach'
        when a.original_season ilike '%survivor%'            then 'Survivor'
        when a.original_season ilike '%big brother%'         then 'Big Brother'
        when a.original_season ilike '%amazing race%'        then 'The Amazing Race'
        when a.original_season ilike '%love island%'         then 'Love Island'
        when a.original_season ilike '%geordie shore%'       then 'Geordie Shore'
        when a.original_season ilike '%too hot to handle%'   then 'Too Hot to Handle'
        when a.original_season ilike '%floribama%'           then 'Floribama Shore'
        when a.original_season ilike '%traitors%'            then 'The Traitors'
        when a.original_season ilike '%challenge%'           then 'The Challenge'
        when a.original_season ilike '%n/a%'
          or a.original_season = '—'                         then 'None (new to TV)'
        when a.original_season is null                       then null
        else 'Other'
    end                                                               as origin_show,
    -- "Big Brother 20" vs "Big Brother UK 17": only US versions can link to
    -- the Survivor / Big Brother data in this warehouse.
    case
        when a.original_season is null then null
        when regexp_matches(lower(a.original_season),
             'turkey|român|roman|spain|españa|uk\b|nigeria|australia|canada|celebrity|brasil|brazil|mexic|argentin|south africa|new zealand|over the top')
             then false
        else true
    end                                                               as origin_is_us_version,
    a.finish_raw,
    case
        when a.finish_raw ilike 'winner%'
          or a.finish_raw ilike 'champion%'                  then 'winner'
        when a.finish_raw ilike 'runner%'
          or a.finish_raw ilike '%second place%'             then 'runner_up'
        when a.finish_raw ilike '%third place%'              then 'third_place'
        when a.finish_raw ilike '%place%'
          or a.finish_raw ilike 'finalist%'                  then 'finalist'
        when a.finish_raw ilike '%disqualified%'             then 'disqualified'
        when a.finish_raw ilike '%quit%'
          or a.finish_raw ilike '%withdr%'
          or a.finish_raw ilike '%left%'                     then 'quit'
        when a.finish_raw ilike '%medical%'
          or a.finish_raw ilike '%injur%'                    then 'medical'
        when a.finish_raw ilike '%eliminated%'
          or a.finish_raw ilike '%voted off%'
          or a.finish_raw ilike '%lost%'
          or a.finish_raw ilike 'episode%'                   then 'eliminated'  -- "Episode 8" = out in episode 8
        when a.finish_raw ilike '%removed%'                  then 'removed'
    end                                                               as finish_type,
    try_cast(regexp_extract(a.finish_raw, 'Episode (\d+)', 1) as integer) as exit_episode
from names as n
left join row_attributes as a
    on n.season_key = a.season_key
   and n.table_index = a.table_index
   and n.row_index = a.row_index
