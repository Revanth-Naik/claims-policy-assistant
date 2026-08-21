-- Grain: one row per claim line. This is the fact table the Streamlit app's
-- structured-lookup half of the retriever queries directly, and what a
-- Power BI / BI tool would sit on top of.
select
    e.claim_id,
    e.claim_line_id,
    dm.member_sk,
    e.member_id,
    dp.provider_sk,
    e.provider_id,
    e.service_date,
    e.submitted_date,
    e.days_to_submit,
    e.plan_type_at_service,
    e.member_region,
    e.specialty,
    e.network_status,
    e.procedure_code,
    e.procedure_desc,
    e.billed_amount,
    e.allowed_amount,
    e.paid_amount,
    e.claim_status,
    e.denial_reason_code,
    e.denial_reason_desc,
    e.is_auth_related_denial,
    e.place_of_service
from {{ ref('int_claims_enriched') }} e
left join {{ ref('dim_members') }} dm
    on e.member_id = dm.member_id
    and e.service_date >= dm.valid_from
    and (e.service_date < dm.valid_to or dm.valid_to is null)
left join {{ ref('dim_providers') }} dp
    on e.provider_id = dp.provider_id
