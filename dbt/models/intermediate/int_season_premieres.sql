-- Premiere and finale dates for Big Brother and Challenge seasons, read from
-- the "Episodes" table on each season page (survivoR already has dates).
-- Dates are needed to put a person's appearances in career order across shows.
with cells as (
    select 'bigbrother' as show_name, t.season_key, c.table_index, c.row_index, c.value
    from {{ source('bigbrother', 'wiki_tables') }} as t
    inner join {{ source('bigbrother', 'wiki_cells') }} as c
        on c.season_key = t.season_key and c.table_index = t.table_index
    where t.section ilike 'episodes%'
      and c.column_header ilike '%date%'

    union all

    select 'challenge', t.season_key, c.table_index, c.row_index, c.value
    from {{ source('challenge', 'wiki_tables') }} as t
    inner join {{ source('challenge', 'wiki_cells') }} as c
        on c.season_key = t.season_key and c.table_index = t.table_index
    where t.section ilike 'episodes%'
      and c.column_header ilike '%date%'
),

parsed as (
    select
        show_name,
        season_key,
        table_index,
        row_index,
        -- "July 5, 2000" (footnotes and hidden ISO dates were stripped at load)
        cast(try_strptime(
            regexp_extract(value, '([A-Z][a-z]+ \d{1,2}, \d{4})', 1), '%B %d, %Y'
        ) as date) as air_date
    from cells
)

-- Premiere = date on the FIRST episode row, finale = date on the LAST one.
-- (Taking min/max over every date let a stray date in the table, e.g. a
-- 1988 reference, become a "premiere". See D012.) Dates before the first
-- season of either show (1998) are ignored as noise.
select
    show_name,
    season_key,
    arg_min(air_date, table_index * 1000 + row_index) as premiered_date,
    arg_max(air_date, table_index * 1000 + row_index) as finale_date
from parsed
where air_date >= date '1998-01-01'
group by show_name, season_key
