# CareFlow — Next Milestone: dbt, BigQuery and PM4Py

This implementation follows the project brief's Week 2 / mid-project review: normalize the event log, discover the as-is process, and verify the simulated event pipeline can be analyzed consistently. It uses the synthetic dataset for reproducibility.

## What is included

- `careflow_dbt/`: dbt BigQuery project with source configuration, staging and intermediate models, analytical marts, schema tests and singular SQL tests.
- `scripts/load_synthetic_to_bigquery.py`: typed loader for the synthetic CSV. It refuses rows unless all are explicitly marked synthetic. It replaces the selected demo table (`WRITE_TRUNCATE`).
- `scripts/run_pm4py_discovery.py`: exports directly-follows edges, variants and baseline conformance. When PM4Py is installed, it additionally exports PM4Py DFG frequencies, start/end activities and an inductive Petri-net PNML file.
- `scripts/audit_event_log.py`: produces a machine-readable pre-ingestion quality report.
- `tests/test_careflow_event_log.py`: regression tests for the local synthetic event log.

## Local verification

From the repository root:

```bash
python scripts/audit_event_log.py
python scripts/run_pm4py_discovery.py
python -m unittest discover -s tests -v
```

PM4Py output requires the packages in `requirements.txt`; if PM4Py is absent the script still emits transparent native event-log analysis artifacts. To require PM4Py specifically, run:

```bash
python scripts/run_pm4py_discovery.py --require-pm4py
```

## BigQuery setup

1. Create or select a Google Cloud project with BigQuery enabled.
2. Install the optional cloud stack: `pip install -r requirements-cloud.txt`.
3. Authenticate using the organization's approved process. For personal development this may be `gcloud auth application-default login`; production should use a least-privilege service identity managed according to organizational policy.
4. Set `GCP_PROJECT_ID` and optionally `BIGQUERY_LOCATION` in the shell.
5. Load only the demo data:

   ```bash
   python scripts/load_synthetic_to_bigquery.py --dataset careflow_raw --table raw_event_log
   ```

   **Warning:** this loader uses `WRITE_TRUNCATE` for the specified destination table. Use it only for the dedicated synthetic demo table.

## Run dbt

Copy `careflow_dbt/profiles.yml.example` to `~/.dbt/profiles.yml` and configure the project/profile values for your environment. The profile uses OAuth credentials obtained through the configured Google Cloud authentication flow.

```bash
cd careflow_dbt
dbt debug
dbt run
dbt test
```

The raw source defaults to `careflow_raw.raw_event_log`; dbt writes transformed outputs to the profile's target dataset (default `careflow_analytics`) using `staging`, `intermediate`, and `marts` custom schemas. Override the source dataset with:

```bash
dbt run --vars '{careflow_source_dataset: careflow_raw}'
```

The models create:

- `stg_careflow__events`: typed, standardized event rows.
- `int_careflow__ordered_events`: deterministic event order within each case.
- `int_careflow__event_transitions`: predecessor/successor and inter-event elapsed time.
- `fct_patient_cases`: case throughput and reconstructed activity trace.
- `fct_transition_bottlenecks`: count, mean, median and approximate 90th percentile by transition.
- `fct_triage_loopbacks`: X-Ray → Triage loop indicators.
- `fct_process_variants`: trace frequency and share.
- `fct_conformance_results`: exact-trace comparison with the reference pathway.

## Interpretation and production caveats

- The 40% triage-return rate is deliberately injected into synthetic demo data. It is a test oracle, not a real hospital statistic.
- A gap between recorded events is **inter-event elapsed time**, not pure queue time or service duration. Accurate queue/service metrics require explicit queue-entry, activity-start, and activity-end timestamps.
- The reference pathway is a first-pass exact-sequence baseline. Clinically valid alternatives, emergency escalations, transfers, and incomplete extracts must be defined with process owners before real data is evaluated.
- The dbt ordering uses timestamp, activity name and resource ID to make ties deterministic. Real EHR integrations should preserve and use the source event ID/sequence number for clinically meaningful ordering.
- The cloud load and dbt execution have not been run against a real GCP project in this workspace because cloud credentials/project access were not supplied. Run `dbt debug`, `dbt run`, and `dbt test` in your configured environment before treating the warehouse layer as operational.
- Do not upload real patient records or commit credentials. Use only authorized, de-identified data under the organization's access, retention, and security requirements.
