{{ config(description='First-pass exact-sequence conformance against the explicitly documented reference pathway. Confirm accepted clinical variants with domain owners before production use.') }}

WITH reference_path AS (
    SELECT 'Registration → Triage → Physician Assessment → X-Ray → Physician Reassessment → Treatment → Discharge' AS ideal_trace
)
SELECT
    c.case_id,
    c.case_trace,
    c.case_throughput_minutes,
    c.returned_to_triage_after_xray,
    c.triage_return_reason,
    c.age_band,
    c.arrival_shift,
    c.is_synthetic,
    c.case_trace = r.ideal_trace AS conforms_to_baseline,
    CASE
        WHEN c.returned_to_triage_after_xray
            THEN 'Rework loop: X-Ray → Triage'
        WHEN c.case_trace = r.ideal_trace
            THEN 'No deviation from the reference sequence'
        ELSE 'Other sequence deviation — review with process owner'
    END AS deviation_reason
FROM {{ ref('fct_patient_cases') }} c
CROSS JOIN reference_path r
