{#
  Group free-text "where are they from" notes into origin shows.
  "Big Brother 20" -> Big Brother, "Survivor: Cagayan" -> Survivor,
  "The Real World: Key West" -> The Real World. Non-show notes ("Olympic
  figure skater") -> Other.
  (The Challenge staging has an older inline copy of this logic; this macro
  is the shared version going forward.)
#}
{% macro origin_show(col) -%}
    case
        when {{ col }} ilike '%real world%'          then 'The Real World'
        when {{ col }} ilike '%road rules%'          then 'Road Rules'
        when {{ col }} ilike '%are you the one%'     then 'Are You the One?'
        when {{ col }} ilike '%ex on the beach%'     then 'Ex on the Beach'
        when {{ col }} ilike '%survivor%'            then 'Survivor'
        when {{ col }} ilike '%big brother%'         then 'Big Brother'
        when {{ col }} ilike '%amazing race%'        then 'The Amazing Race'
        when {{ col }} ilike '%love island%'         then 'Love Island'
        when {{ col }} ilike '%real housewives%'     then 'The Real Housewives'
        when {{ col }} ilike '%bachelor%'            then 'The Bachelor franchise'
        when {{ col }} ilike '%below deck%'          then 'Below Deck'
        when {{ col }} ilike '%vanderpump%'          then 'Vanderpump Rules'
        when {{ col }} ilike '%drag race%'           then 'RuPaul''s Drag Race'
        when {{ col }} ilike '%traitors%'            then 'The Traitors'
        when {{ col }} ilike '%challenge%'           then 'The Challenge'
        when {{ col }} is null                       then null
        else 'Other'
    end
{%- endmacro %}

{% macro origin_is_us_version(col) -%}
    case
        when {{ col }} is null then null
        when regexp_matches(lower({{ col }}),
             'turkey|român|roman|spain|españa|uk\b|nigeria|australia|canada|celebrity|brasil|brazil|mexic|argentin|south africa|new zealand|over the top')
             then false
        else true
    end
{%- endmacro %}
