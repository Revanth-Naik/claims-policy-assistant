-- SCD Type 2 dimension: one row per member per plan/region version.
select
    {{ member_surrogate_key() }} as member_sk,
    member_id,
    first_name,
    last_name,
    date_of_birth,
    gender,
    region,
    plan_type,
    valid_from,
    valid_to,
    is_current
from {{ ref('stg_members') }}
