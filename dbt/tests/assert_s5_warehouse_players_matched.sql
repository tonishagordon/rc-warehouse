-- Every S5 player whose cast note names a show in this warehouse must be
-- matched to exactly one person; otherwise their track record would silently
-- go missing from the scouting report.
select name, warehouse_show, count(person_id) as matches
from {{ ref('ml_traitors_s5_cast') }}
where warehouse_show is not null
group by 1, 2
having count(person_id) <> 1
