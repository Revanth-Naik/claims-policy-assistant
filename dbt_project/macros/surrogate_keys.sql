{#
  Small hand-rolled surrogate-key helpers so the project doesn't need the
  dbt_utils package just for md5(concat(...)). In a real Snowflake/production
  setup, swap these for dbt_utils.generate_surrogate_key().
#}

{% macro member_surrogate_key() %}
    md5(cast(member_id as varchar) || '|' || cast(valid_from as varchar))
{% endmacro %}
