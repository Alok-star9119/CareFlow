{{ config(description='Standardizes the raw CareFlow event log into a consistent, typed, process-mining schema.') }}

WITH source_events AS (
    SELECT
        NULLIF(TRIM(CAST(`Case_ID` AS STRING)), '') AS case_id,
        NULLIF(TRIM(CAST(`Activity_Name` AS STRING)), '') AS activity_name,
        SAFE_CAST(`Timestamp` AS DATETIME) AS event_timestamp,
        NULLIF(TRIM(CAST(`Department` AS STRING)), '') AS department,
        NULLIF(TRIM(CAST(`Resource_ID` AS STRING)), '') AS resource_id,
        NULLIF(TRIM(CAST(`Age_Band` AS STRING)), '') AS age_band,
        NULLIF(TRIM(CAST(`Arrival_Shift` AS STRING)), '') AS arrival_shift,
        SAFE_CAST(`Rework_Expected` AS BOOL) AS rework_expected,
        NULLIF(TRIM(CAST(`Return_Reason` AS STRING)), '') AS return_reason,
        SAFE_CAST(`Is_Synthetic` AS BOOL) AS is_synthetic,
        TO_HEX(SHA256(CAST(TO_JSON_STRING(STRUCT(
            `Case_ID` AS case_id,
            `Activity_Name` AS activity_name,
            `Timestamp` AS event_timestamp,
            `Resource_ID` AS resource_id
        )) AS BYTES))) AS source_event_fingerprint
    FROM {{ source('careflow_raw', 'raw_event_log') }}
)
SELECT *
FROM source_events
