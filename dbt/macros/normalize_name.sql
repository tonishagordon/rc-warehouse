{#
  Name normalization used for matching people across sources.
  "Johnny \"Bananas\" Devenanzio" -> "johnny devenanzio"
  "Da'Vonne Rogers"             -> "davonne rogers"
  "Cliff Hogg III"              -> "cliff hogg"
  "Michele Fitzgerald" / "Kaôh Rōng" accents are stripped.
  The quoted nickname is removed here; nickname() returns it separately.
  Unicode spaces (non-breaking U+00A0, thin, narrow no-break) are turned into
  normal spaces FIRST. Otherwise the punctuation step deletes them and
  "Yam Yam Arocho" becomes "yamyamarocho" (D014).
#}

{% macro plain_spaces(col) -%}
    regexp_replace({{ col }}, '[\x{00A0}\x{2002}-\x{200B}\x{202F}\x{205F}\x{3000}]', ' ', 'g')
{%- endmacro %}

{% macro normalize_name(col) -%}
    trim(regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(lower(strip_accents({{ plain_spaces(col) }})), '["“”][^"“”]*["“”]', ' ', 'g'),
                '\b(jr|sr|ii|iii|iv)\b\.?', ' ', 'g'),
            '[^a-z ]', '', 'g'),
        '\s+', ' ', 'g'))
{%- endmacro %}

{% macro nickname(col) -%}
    nullif(trim(regexp_replace(lower(strip_accents(regexp_extract({{ plain_spaces(col) }}, '["“”]([^"“”]+)["“”]', 1))), '[^a-z ]', '', 'g')), '')
{%- endmacro %}
