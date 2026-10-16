{{ config(description='Adds a deterministic within-case event sequence for downstream transitions and trace construction.') }}

SELECT
    *,
    ROW_NUMBER() OVER (
        PARTITION BY case_id
        ORDER BY event_timestamp, activity_name, COALESCE(resource_id, '')
    ) AS event_order
FROM {{ ref('stg_careflow__events') }}
WHERE case_id IS NOT NULL
  AND activity_name IS NOT NULL
  AND event_timestamp IS NOT NULL
