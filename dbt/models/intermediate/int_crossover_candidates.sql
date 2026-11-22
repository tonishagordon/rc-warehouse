-- Review queue: possible same-person pairs that the automatic rules did NOT
-- link, e.g. Big Brother <-> Survivor crossovers (no origin season to block
-- on). Confirmed pairs go into seeds/crosswalk_manual.csv; rejected pairs
-- simply stay here as "looked at, not the same".
with m as (
    select b.person_id, im.*
    from {{ ref('bridge_person_mention') }} as b
    inner join {{ ref('int_person_mentions') }} as im using (mention_key)
),

pairs as (
    select
        a.person_id         as person_id_a,
        a.show_name         as show_a,
        a.season_key        as season_a,
        a.display_name      as name_a,
        b.person_id         as person_id_b,
        b.show_name         as show_b,
        b.season_key        as season_b,
        b.display_name      as name_b,
        greatest(
            case when a.name_norm = b.name_norm then 1.0 end,
            case when a.last_name_norm = b.last_name_norm
                  and (a.nickname_norm in (b.first_name_norm, b.nickname_norm)
                    or b.nickname_norm in (a.first_name_norm, a.nickname_norm)) then 0.97 end,
            jaro_winkler_similarity(a.name_norm, b.name_norm)
        )                   as score
    from m as a
    inner join m as b
        on a.show_name < b.show_name                -- different shows, each pair once
       and a.person_id <> b.person_id               -- not already linked
       and a.last_name_norm = b.last_name_norm      -- block on surname
    where a.name_norm like '% %' and b.name_norm like '% %'
      and a.origin_season_key is null
      and b.origin_season_key is null
),

rejected as (
    -- Pairs reviewed and marked 'different' in the crosswalk seed, resolved to
    -- PEOPLE: once two people are judged different, every season pairing of
    -- them is silenced (not just the one season pair written in the seed).
    select distinct ma.person_id as person_id_a, mb.person_id as person_id_b
    from {{ ref('crosswalk_manual') }} as r
    inner join m as ma
        on ma.show_name = r.show_a and ma.season_key = r.season_a
       and ma.name_norm = {{ normalize_name('r.name_a') }}
    inner join m as mb
        on mb.show_name = r.show_b and mb.season_key = r.season_b
       and mb.name_norm = {{ normalize_name('r.name_b') }}
    where lower(r.decision) = 'different'
)

select p.*
from pairs as p
where p.score >= 0.90
  and not exists (
      select 1 from rejected as r
      where (r.person_id_a = p.person_id_a and r.person_id_b = p.person_id_b)
         or (r.person_id_a = p.person_id_b and r.person_id_b = p.person_id_a)
  )
-- one row per pair of people; show each person's EARLIEST season in that show
qualify row_number() over (partition by p.person_id_a, p.person_id_b
                          order by p.score desc, p.season_a, p.season_b) = 1
