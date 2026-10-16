-- A failing result indicates potentially duplicated event rows. Review source identifiers
-- before deduplicating because repeated identical activities can be legitimate in some systems.
SELECT
    case_id,
    activity_name,
    event_timestamp,
    resource_id,
    COUNT(*) AS duplicate_count
FROM {{ ref('stg_careflow__events') }}
GROUP BY case_id, activity_name, event_timestamp, resource_id
HAVING COUNT(*) > 1
