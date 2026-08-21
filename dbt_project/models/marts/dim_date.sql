-- Date spine covering every claim service date. Uses DuckDB's generate_series;
-- on Snowflake, swap this CTE for a generator-table approach
-- (e.g. TABLE(GENERATOR(ROWCOUNT => N)) + DATEADD), everything downstream
-- (fct_claims joins on date_day) stays identical.
with bounds as (
    select
        min(service_date) as min_date,
        max(service_date) as max_date
    from {{ ref('stg_claims') }}
),

spine as (
    select cast(unnest(generate_series(min_date, max_date, interval 1 day)) as date) as date_day
    from bounds
)

select
    date_day,
    extract(year from date_day)  as year,
    extract(month from date_day) as month,
    extract(day from date_day)   as day,
    extract(dow from date_day)   as day_of_week,
    strftime(date_day, '%B')     as month_name,
    extract(quarter from date_day) as quarter
from spine
