-- Entity resolution, step 3: connected components. Every mention reachable
-- from another through any chain of edges is the same person. The cluster
-- label is the smallest node key in the group (deterministic).
with recursive

edges as (
    select a, b from {{ ref('int_person_edges') }}
    union
    select b, a from {{ ref('int_person_edges') }}
),

mentions as (
    select mention_key from {{ ref('int_person_mentions') }}
),

nodes as (
    select a as node from edges
    union
    select mention_key from mentions
),

reach(node, root) as (
    select node, node from nodes
    union
    select e.b, r.root
    from reach as r
    inner join edges as e on e.a = r.node
)

select
    r.node              as mention_key,
    min(r.root)         as cluster_root
from reach as r
inner join mentions as m on m.mention_key = r.node
group by r.node
