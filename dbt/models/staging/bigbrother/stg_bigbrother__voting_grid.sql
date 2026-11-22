-- The "Voting history" grid, unpivoted: one row per (row label, column) cell.
-- Rows are either EVENT rows (Head of Household, Nominations, Veto, Evicted,
-- twist winners) or HOUSEGUEST rows (that houseguest's status/vote each week).
-- Labels are what Wikipedia shows (often nicknames like "Boogie"); matching
-- them to full names in stg_bigbrother__houseguests happens in intermediate.
with voting_tables as (
    select season_key, min(table_index) as table_index
    from {{ source('bigbrother', 'wiki_tables') }}
    where section = 'Voting history'
    group by season_key
),

cells as (
    select c.season_key, c.row_index, c.col_index, c.column_header, c.value
    from {{ source('bigbrother', 'wiki_cells') }} as c
    inner join voting_tables as t
        on c.season_key = t.season_key
       and c.table_index = t.table_index
),

labels as (
    select season_key, row_index, value as row_label
    from cells
    where col_index = 0
),

grid as (
    select
        c.season_key,
        c.row_index,
        l.row_label,
        c.col_index,
        c.column_header,
        c.value
    from cells as c
    inner join labels as l
        on c.season_key = l.season_key
       and c.row_index = l.row_index
    where c.col_index > 0
),

classified as (
    select
        *,
        regexp_matches(
            lower(row_label),
            'evicted|nomination|head|veto|winner|competition|decision|m\.v\.p|votes? to (evict|win)'
        )                                                           as is_event_row,
        try_cast(regexp_extract(column_header, 'Week (\d+)', 1) as integer) as week_number,
        try_cast(regexp_extract(column_header, 'Day (\d+)', 1) as integer)  as column_day,
        (column_header ilike '%finale%')                            as is_finale_column_by_header
    from grid
),

-- Some seasons label the final column "Week 11" instead of "Finale" (BB04).
-- A column is also the finale if its result row says "votes to win".
finale_by_result as (
    select distinct season_key, col_index
    from classified
    where is_event_row
      and value ilike '%vote% to win%'
),

flagged as (
    select
        c.*,
        (c.is_finale_column_by_header or f.col_index is not null) as is_finale_column
    from classified as c
    left join finale_by_result as f
        on c.season_key = f.season_key
       and c.col_index = f.col_index
)

-- Wikipedia sometimes repeats a footer row (e.g. "Evicted" twice); keep one copy.
select distinct
    season_key,
    cast(substr(season_key, 3) as integer) as season_number,
    row_label,
    is_event_row,
    col_index,
    column_header,
    week_number,
    column_day,
    is_finale_column,
    value
from flagged
