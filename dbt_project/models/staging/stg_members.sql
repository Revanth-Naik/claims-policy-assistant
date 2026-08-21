-- Light cleanup/casting on the raw members seed. Kept 1:1 with the source
-- grain (one row per member per SCD2 version) -- no business logic here.
select
    member_id,
    first_name,
    last_name,
    cast(dob as date)        as date_of_birth,
    gender,
    region,
    plan_type,
    cast(valid_from as date) as valid_from,
    cast(valid_to as date)   as valid_to,
    cast(is_current as boolean) as is_current
from {{ ref('members') }}
