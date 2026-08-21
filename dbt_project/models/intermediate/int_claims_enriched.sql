-- Central piece of "reusable business logic": every claim is matched to the
-- member record that was ACTIVE ON THE DATE OF SERVICE, not the member's
-- current plan. This as-of join against the SCD Type 2 member history is
-- exactly what makes plan_type_at_service trustworthy for reporting -- a
-- naive join to "current" member data would silently mislabel any claim
-- that happened before a member's plan change.
with claims as (
    select * from {{ ref('stg_claims') }}
),

members as (
    select * from {{ ref('stg_members') }}
),

providers as (
    select * from {{ ref('stg_providers') }}
),

claims_with_member_asof as (
    select
        c.*,
        m.plan_type   as plan_type_at_service,
        m.region      as member_region,
        m.valid_from  as member_version_valid_from
    from claims c
    left join members m
        on c.member_id = m.member_id
        and c.service_date >= m.valid_from
        and (c.service_date < m.valid_to or m.valid_to is null)
)

select
    cwm.claim_id,
    cwm.claim_line_id,
    cwm.member_id,
    cwm.member_region,
    cwm.plan_type_at_service,
    cwm.provider_id,
    p.provider_name,
    p.specialty,
    p.network_status,
    cwm.service_date,
    cwm.submitted_date,
    datediff('day', cwm.service_date, cwm.submitted_date) as days_to_submit,
    cwm.procedure_code,
    cwm.procedure_desc,
    cwm.billed_amount,
    cwm.allowed_amount,
    cwm.paid_amount,
    cwm.claim_status,
    cwm.denial_reason_code,
    cwm.denial_reason_desc,
    cwm.place_of_service,
    case when cwm.denial_reason_code = 'CO-197' then true else false end as is_auth_related_denial
from claims_with_member_asof cwm
left join providers p on cwm.provider_id = p.provider_id
