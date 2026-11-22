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
                   or column_header ilike '%known f%'             then value end) as original_season,
        max(case when column_header ilike '%finish%'
                   or column_header ilike 'result%'               then value end) as finish_raw
    from cells
    group by season_key, table_index, row_index
),

names as (
    select season_key, table_index, row_index, col_index, column_header, value as contestant_name
    from cells
    where regexp_matches(lower(column_header),
              'contestant|partner|^cast|^name|player|mercenar|veteran|rookie|relative|famil|challenger|champion|member|pro|alumni|fresh meat|bloodline')
      and not regexp_matches(lower(column_header), 'original|known f|finish|result|episode|relation')
      and value is not null
      and value <> column_header            -- repeated header rows
),

joined as (
    select
        n.season_key || '_' || n.table_index || '_' || lpad(cast(n.row_index as varchar), 2, '0')
            || '_' || n.col_index                                     as contestant_key,
        n.season_key,
        n.contestant_name,
        n.column_header,
        -- Paired formats list two people per row but only one Original season:
        -- Fresh Meat seasons pair a veteran with a rookie, Battle of the
        -- Bloodlines pairs a veteran with a relative. The second person's
        -- origin comes from the column they're in. See D007.
        case
            when n.column_header ilike 'fresh meat%' then 'The Challenge: Fresh Meat (rookie)'
            when n.column_header ilike 'bloodline%'  then 'Bloodline relative (new to TV)'
            else a.original_season
        end                                                           as original_season,
        a.finish_raw
    from names as n
    left join row_attributes as a
        on n.season_key = a.season_key
       and n.table_index = a.table_index
       and n.row_index = a.row_index
)

select
    contestant_key,
    season_key,
    contestant_name,
    case
        when column_header ilike 'female%' then 'Female'
        when column_header ilike 'male%'   then 'Male'
    end                                                               as gender_from_table,
    (column_header ilike '%mercenar%')                                as is_mercenary,
    original_season,
    case
        when original_season ilike '%real world%'          then 'The Real World'
        when original_season ilike '%road rules%'          then 'Road Rules'
        when original_season ilike '%fresh meat%'          then 'The Challenge: Fresh Meat'
        when original_season ilike '%are you the one%'     then 'Are You the One?'
        when original_season ilike '%ex on the beach%'     then 'Ex on the Beach'
        when original_season ilike '%survivor%'            then 'Survivor'
        when original_season ilike '%big brother%'         then 'Big Brother'
        when original_season ilike '%amazing race%'        then 'The Amazing Race'
        when original_season ilike '%love island%'         then 'Love Island'
        when original_season ilike '%geordie shore%'       then 'Geordie Shore'
        when original_season ilike '%too hot to handle%'   then 'Too Hot to Handle'
        when original_season ilike '%floribama%'           then 'Floribama Shore'
        when original_season ilike '%traitors%'            then 'The Traitors'
        when original_season ilike '%challenge%'           then 'The Challenge'
        when original_season ilike '%n/a%'
          or original_season = '—'
          or original_season ilike '%new to tv%'           then 'None (new to TV)'
        when original_season is null                       then null
        else 'Other'
    end                                                               as origin_show,
    -- "Big Brother 20" vs "Big Brother UK 17": only US versions can link to
    -- the Survivor / Big Brother data in this warehouse.
    case
        when original_season is null then null
        when regexp_matches(lower(original_season),
             'turkey|român|roman|spain|españa|uk\b|nigeria|australia|canada|celebrity|brasil|brazil|mexic|argentin|south africa|new zealand|over the top')
             then false
        else true
    end                                                               as origin_is_us_version,
    finish_raw,
    case
        when finish_raw ilike 'winner%'
          or finish_raw ilike 'champion%'                  then 'winner'
        when finish_raw ilike 'runner%'
          or finish_raw ilike '%second place%'             then 'runner_up'
        when finish_raw ilike '%third place%'              then 'third_place'
        when finish_raw ilike '%place%'
          or finish_raw ilike 'finalist%'                  then 'finalist'
        when finish_raw ilike '%disqualified%'             then 'disqualified'
        when finish_raw ilike '%quit%'
          or finish_raw ilike '%withdr%'
          or finish_raw ilike '%left%'                     then 'quit'
        when finish_raw ilike '%medical%'
          or finish_raw ilike '%injur%'                    then 'medical'
        when finish_raw ilike '%eliminated%'
          or finish_raw ilike '%voted off%'
          or finish_raw ilike '%lost%'
          or finish_raw ilike 'episode%'                   then 'eliminated'  -- "Episode 8" = out in episode 8
        when finish_raw ilike '%removed%'                  then 'removed'
    end                                                               as finish_type,
    try_cast(regexp_extract(finish_raw, 'Episode (\d+)', 1) as integer) as exit_episode
from joined
