select
    md5(provider_id) as provider_sk,
    provider_id,
    provider_name,
    npi,
    specialty,
    region,
    network_status
from {{ ref('stg_providers') }}
