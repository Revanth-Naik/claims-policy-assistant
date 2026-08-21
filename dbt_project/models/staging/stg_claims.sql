select
    claim_id,
    claim_line_id,
    member_id,
    provider_id,
    cast(service_date as date)   as service_date,
    cast(submitted_date as date) as submitted_date,
    procedure_code,
    procedure_desc,
    cast(billed_amount as decimal(10,2))   as billed_amount,
    cast(allowed_amount as decimal(10,2))  as allowed_amount,
    cast(paid_amount as decimal(10,2))     as paid_amount,
    claim_status,
    denial_reason_code,
    denial_reason_desc,
    place_of_service
from {{ ref('claims') }}
