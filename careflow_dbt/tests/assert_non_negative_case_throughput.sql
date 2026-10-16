SELECT case_id, case_throughput_minutes
FROM {{ ref('fct_patient_cases') }}
WHERE case_throughput_minutes < 0
