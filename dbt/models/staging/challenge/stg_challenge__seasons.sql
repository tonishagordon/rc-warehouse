-- One row per in-scope Challenge season (main MTV series + US spin-offs).
select
    season_key,
    case
        when season_key like 'CUSA%' then 'The Challenge: USA'
        when season_key like 'CAS%'  then 'The Challenge: All Stars'
        when season_key like 'CVP%'
          or season_key like 'CVS%'  then 'The Challenge: Champs vs.'
        when season_key like 'CWC%'  then 'The Challenge: World Championship'
        else 'The Challenge'
    end                                 as series,
    cast("order" as integer)            as season_number,
    title                               as season_title,
    page_title                          as wikipedia_page
from {{ source('challenge', 'season_index') }}
where upper(include) = 'Y'
