{#
  Name normalization used for matching people across sources.
  "Johnny \"Bananas\" Devenanzio" -> "johnny devenanzio"
  "Da'Vonne Rogers"             -> "davonne rogers"
  "Cliff Hogg III"              -> "cliff hogg"
  "Michele Fitzgerald" / "Kaôh Rōng" accents are stripped.
  The quoted nickname is removed here; nickname() returns it separately.
#}
{% macro normalize_name(col) -%}
    trim(regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(lower(strip_accents({{ col }})), '["“”][^"“”]*["“”]', ' ', 'g'),
                '\b(jr|sr|ii|iii|iv)\b\.?', ' ', 'g'),
            '[^a-z ]', '', 'g'),
        '\s+', ' ', 'g'))
{%- endmacro %}

{% macro nickname(col) -%}
    nullif(regexp_replace(lower(strip_accents(regexp_extract({{ col }}, '["“”]([^"“”]+)["“”]', 1))), '[^a-z ]', '', 'g'), '')
{%- endmacro %}
