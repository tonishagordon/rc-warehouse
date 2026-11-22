-- One row per contestant per Traitors season, from the "Contestants" table.
-- Season 1 mixed civilians and celebrities, so its column is
-- "Occupation/Original series"; later seasons use "Notability/Debut series".
with cast_tables as (
    select season_key, min(table_index) as table_index
    from {{ source('traitors', 'wiki_tables') }}
    where section ilike 'contestants'
    group by season_key
),

cells as (
    select c.season_key, c.row_index, c.column_header, c.value
    from {{ source('traitors', 'wiki_cells') }} as c
    inner join cast_tables as t
        on c.season_key = t.season_key and c.table_index = t.table_index
),

pivoted as (
    select
        season_key,
        row_index,
        max(case when column_header ilike 'contestant%'                  then value end) as contestant_name,
        max(case when column_header ilike 'age%'                         then value end) as age_raw,
        max(case when column_header ilike 'from%'                        then value end) as hometown,
        max(case when column_header ilike '%notability%'
                   or column_header ilike '%original series%'            then value end) as notability,
        max(case when column_header ilike 'affiliation%'                 then value end) as affiliation,
        max(case when column_header ilike 'finish%'                      then value end) as finish_raw
    from cells
    group by season_key, row_index
)

select
    season_key || '_' || lpad(cast(row_index as varchar), 2, '0')       as contestant_key,
    season_key,
    cast(substr(season_key, 3) as integer)                              as season_number,
    contestant_name,
    try_cast(regexp_extract(age_raw, '(\d+)', 1) as integer)            as age_at_filming,
    hometown,
    notability,
    {{ origin_show('notability') }}                                     as origin_show,
    {{ origin_is_us_version('notability') }}                            as origin_is_us_version,
    affiliation,
    case
        when affiliation ilike '%traitor%'  then 'Traitor'
        when affiliation ilike '%faithful%' then 'Faithful'
    end                                                                 as role,
    (affiliation ilike 'secret%')                                       as is_secret_traitor,
    finish_raw,
    case
        when finish_raw ilike 'winner%'     then 'winner'
        when finish_raw ilike 'runner%'     then 'runner_up'
        when finish_raw ilike 'murdered%'   then 'murdered'
        when finish_raw ilike 'banished%'   then 'banished'
        when finish_raw ilike 'walked%'
          or finish_raw ilike 'quit%'
          or finish_raw ilike 'withdr%'     then 'walked'
        when finish_raw ilike 'eliminated%' then 'eliminated'
    end                                                                 as finish_type,
    try_cast(regexp_extract(finish_raw, 'Episode (\d+)', 1) as integer) as exit_episode
from pivoted
where contestant_name is not null
  and contestant_name not ilike 'contestant%'     -- repeated header rows
