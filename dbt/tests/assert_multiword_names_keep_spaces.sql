-- Guard for D014: a multi-word display name must normalize to a multi-word
-- name. If spaces vanish ("yamyamarocho"), a hidden character slipped
-- through normalization and the person can't be matched by first/last name.
{{ config(severity='warn') }}

select show_name, season_key, display_name, name_norm
from {{ ref('int_person_mentions') }}
where regexp_matches(trim(display_name), '\S\s+\S')
  and name_norm not like '% %'
