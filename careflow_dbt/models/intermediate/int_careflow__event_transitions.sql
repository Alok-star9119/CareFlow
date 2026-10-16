{{ config(description='Creates one row per event with its preceding/following activity and elapsed time to the next recorded event.') }}

WITH sequenced AS (
    SELECT
        *,
        LAG(activity_name) OVER case_sequence AS previous_activity,
        LEAD(activity_name) OVER case_sequence AS next_activity,
        LEAD(event_timestamp) OVER case_sequence AS next_event_timestamp,
        LEAD(return_reason) OVER case_sequence AS next_return_reason
    FROM {{ ref('int_careflow__ordered_events') }}
    WINDOW case_sequence AS (
        PARTITION BY case_id
        ORDER BY event_order
    )
)
SELECT
    *,
    CASE
        WHEN next_event_timestamp IS NOT NULL
        THEN SAFE_DIVIDE(DATETIME_DIFF(next_event_timestamp, event_timestamp, SECOND), 60.0)
        ELSE NULL
    END AS elapsed_to_next_minutes
FROM sequenced
