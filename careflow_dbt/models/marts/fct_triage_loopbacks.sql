{{ config(description='Case-level facts for the specific X-Ray → Triage rework pattern highlighted in the CareFlow brief.') }}

SELECT
    case_id,
    COUNTIF(activity_name = 'X-Ray' AND next_activity = 'Triage') AS xray_to_triage_loop_count,
    COUNTIF(activity_name = 'X-Ray' AND next_activity = 'Triage') > 0 AS returned_to_triage_after_xray,
    ARRAY_AGG(
        IF(activity_name = 'X-Ray' AND next_activity = 'Triage', next_return_reason, NULL)
        IGNORE NULLS ORDER BY event_order LIMIT 1
    )[SAFE_OFFSET(0)] AS triage_return_reason,
    LOGICAL_OR(COALESCE(is_synthetic, FALSE)) AS is_synthetic
FROM {{ ref('int_careflow__event_transitions') }}
GROUP BY case_id
