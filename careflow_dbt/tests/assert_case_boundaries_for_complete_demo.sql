-- This assertion is appropriate for the complete synthetic demo only. For real EHR extracts,
-- partial windows and transfers may omit Registration or Discharge; adapt this test first.
SELECT case_id
FROM {{ ref('fct_patient_cases') }}
WHERE registration_event_count < 1
   OR discharge_event_count < 1
