{{ config(description='Counts unique patient activity traces and calculates their share of all cases.') }}

WITH variants AS (
    SELECT
        case_trace,
        COUNT(*) AS case_count,
        AVG(case_throughput_minutes) AS mean_throughput_minutes
    FROM {{ ref('fct_patient_cases') }}
    GROUP BY case_trace
)
SELECT
    case_trace,
    case_count,
    mean_throughput_minutes,
    100.0 * SAFE_DIVIDE(case_count, SUM(case_count) OVER ()) AS share_percent
FROM variants
ORDER BY case_count DESC, case_trace
