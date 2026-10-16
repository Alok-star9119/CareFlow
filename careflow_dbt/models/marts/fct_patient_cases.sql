{{ config(description='One row per patient case with throughput, trace, and return-loop indicators.') }}

WITH event_rollup AS (
    SELECT
        case_id,
        MIN(IF(activity_name = 'Registration', event_timestamp, NULL)) AS arrival_timestamp,
        MAX(IF(activity_name = 'Discharge', event_timestamp, NULL)) AS discharge_timestamp,
        COUNT(*) AS activity_count,
        ARRAY_TO_STRING(ARRAY_AGG(activity_name ORDER BY event_order), ' → ') AS case_trace,
        COUNTIF(activity_name = 'Registration') AS registration_event_count,
        COUNTIF(activity_name = 'Discharge') AS discharge_event_count,
        ARRAY_AGG(age_band IGNORE NULLS ORDER BY event_order LIMIT 1)[SAFE_OFFSET(0)] AS age_band,
        ARRAY_AGG(arrival_shift IGNORE NULLS ORDER BY event_order LIMIT 1)[SAFE_OFFSET(0)] AS arrival_shift,
        LOGICAL_OR(COALESCE(is_synthetic, FALSE)) AS is_synthetic
    FROM {{ ref('int_careflow__ordered_events') }}
    GROUP BY case_id
),
loop_rollup AS (
    SELECT
        case_id,
        COUNTIF(activity_name = 'X-Ray' AND next_activity = 'Triage') AS xray_to_triage_loop_count,
        ARRAY_AGG(next_return_reason IGNORE NULLS ORDER BY event_order LIMIT 1)[SAFE_OFFSET(0)] AS triage_return_reason
    FROM {{ ref('int_careflow__event_transitions') }}
    GROUP BY case_id
)
SELECT
    e.case_id,
    e.arrival_timestamp,
    e.discharge_timestamp,
    DATETIME_DIFF(e.discharge_timestamp, e.arrival_timestamp, SECOND) / 60.0 AS case_throughput_minutes,
    e.activity_count,
    e.case_trace,
    e.registration_event_count,
    e.discharge_event_count,
    COALESCE(l.xray_to_triage_loop_count, 0) AS xray_to_triage_loop_count,
    COALESCE(l.xray_to_triage_loop_count, 0) > 0 AS returned_to_triage_after_xray,
    l.triage_return_reason,
    e.age_band,
    e.arrival_shift,
    e.is_synthetic
FROM event_rollup e
LEFT JOIN loop_rollup l USING (case_id)
