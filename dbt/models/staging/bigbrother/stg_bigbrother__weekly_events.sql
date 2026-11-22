-- Event rows from the Voting history grid: who was Head of Household,
-- nominated, won the Veto, and was evicted, per voting column.
-- Multi-name cells (e.g. three initial nominees) are kept as one string here;
-- splitting them against the season's known labels happens in intermediate.
select
    season_key,
    season_number,
    col_index,
    column_header,
    week_number,
    column_day,
    is_finale_column,
    row_label,
    case
        when row_label ilike 'head%household'                       then 'hoh'
        when row_label ilike 'nominations (initial)'
          or row_label ilike 'nominations (pre-veto)'
          or row_label = 'Nominations'                              then 'nominations_initial'
        when row_label ilike 'nominations (final)'
          or row_label ilike 'nominations (post-veto)'              then 'nominations_final'
        when row_label ilike 'veto winner%'                         then 'veto_winner'
        when row_label = 'Evicted'                                  then 'evicted'
        else 'twist'
    end                                                             as event_type,
    value
from {{ ref('stg_bigbrother__voting_grid') }}
where is_event_row
  and value is not null
