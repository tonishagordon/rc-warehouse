{#- Lowercase, strip accents, turn every run of non-letters into one space and
    pad with spaces, so contains(word_pad(a), word_pad(b)) is a whole-word match:
    "Mike "Boogie" Malin" -> ' mike boogie malin ' contains ' boogie '. -#}
{% macro word_pad(col) -%}
(' ' || trim(regexp_replace(lower(strip_accents({{ col }})), '[^a-z]+', ' ', 'g')) || ' ')
{%- endmacro %}
