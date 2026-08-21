select
    provider_id,
    provider_name,
    npi,
    specialty,
    region,
    network_status
from {{ ref('providers') }}
