{{ config(description='Ranks observed activity transitions by elapsed time between event timestamps. This is not pure queue or service time.') }}

SELECT
    activity_name,
    next_activity,
    CONCAT(activity_name, ' → ', next_activity) AS transition,
    COUNT(*) AS transition_count,
    AVG(elapsed_to_next_minutes) AS mean_elapsed_minutes,
    APPROX_QUANTILES(elapsed_to_next_minutes, 100)[SAFE_OFFSET(50)] AS median_elapsed_minutes,
    APPROX_QUANTILES(elapsed_to_next_minutes, 100)[SAFE_OFFSET(90)] AS p90_elapsed_minutes
FROM {{ ref('int_careflow__event_transitions') }}
WHERE next_activity IS NOT NULL
  AND elapsed_to_next_minutes IS NOT NULL
  AND elapsed_to_next_minutes >= 0
GROUP BY activity_name, next_activity
