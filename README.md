# CareFlow — Clinical Pathway Process Mining

CareFlow is a healthcare operations analytics prototype for reconstructing patient journeys from timestamped event logs, identifying process variations, measuring elapsed time between recorded events, and checking journeys against a defined reference pathway.

> **Synthetic-data notice:** all included records are generated for software testing. The generator deliberately injects an `X-Ray → Triage` return into 40% of cases. This is a controlled test scenario, not a statistic about a real hospital and not evidence that any intervention improves patient care.

## Problem and intended outcome

Traditional healthcare dashboards can show aggregate measures such as average emergency-room throughput, but those summaries alone do not explain the sequence of activities behind delays and rework. CareFlow reconstructs each visit as an ordered trace so process owners can investigate common paths, rework loops, long gaps between recorded events, and deviations from a documented reference pathway.

The project brief's target architecture uses BigQuery for event-log storage, dbt for normalization, PM4Py for process discovery, and Power BI or Looker for operational reporting. This repository now contains the local prototype plus the next-milestone BigQuery/dbt scaffolding and PM4Py runner. A live connection to a Google Cloud project and a BI dashboard are not configured here.

## Implemented capabilities

- Generate a reproducible synthetic EHR event log with `Case_ID`, `Activity_Name`, and `Timestamp`.
- Validate required fields, timestamp parsing, duplicate event keys, complete demo case boundaries, and the measured synthetic loopback rate.
- Calculate case throughput, activity traces, process variants, and transition-level inter-event elapsed-time metrics.
- Export a directed directly-follows graph and patient-journey timelines from the notebook.
- Compare each observed case trace with the documented baseline pathway.
- Export CSV artifacts for warehouse and BI consumption.
- Run a standalone process-discovery command that emits native directly-follows / variant / baseline-conformance files and, when PM4Py is installed, PM4Py DFG results and an inductively discovered Petri-net model.
- Provide a dbt project for BigQuery with staging, intermediate, and mart models; schema tests; and singular SQL quality tests.
- Provide a guarded loader that only uploads records marked synthetic to a specified BigQuery demo table.

## Repository structure

```text
CareFlow_Project/
├── CareFlow_Clinical_Pathway_Process_Mining.ipynb
├── README.md
├── requirements.txt
├── requirements-cloud.txt
├── .gitignore
├── careflow_data/
│   ├── raw_event_log.csv
│   ├── clean_event_log.csv
│   ├── case_metrics.csv
│   ├── transition_bottlenecks.csv
│   ├── process_variants.csv
│   ├── process_transitions.csv
│   ├── conformance_results.csv
│   └── data_quality_report.csv
├── scripts/
│   ├── audit_event_log.py
│   ├── run_pm4py_discovery.py
│   └── load_synthetic_to_bigquery.py
├── tests/
│   └── test_careflow_event_log.py
├── docs/
│   └── WAREHOUSE_AND_PROCESS_MINING.md
└── careflow_dbt/
    ├── dbt_project.yml
    ├── profiles.yml.example
    ├── models/
    │   ├── sources.yml
    │   ├── schema.yml
    │   ├── staging/
    │   ├── intermediate/
    │   └── marts/
    └── tests/
```

## Run the local prototype

Python 3.10 or newer is recommended. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
jupyter lab CareFlow_Clinical_Pathway_Process_Mining.ipynb
```

Run the notebook cells from beginning to end. It generates deterministic sample data using a fixed random seed and writes CSV outputs into `careflow_data/`.

## Run the audit, process-discovery exports, and tests

```bash
python scripts/audit_event_log.py
python scripts/run_pm4py_discovery.py
python -m unittest discover -s tests -v
```

To make PM4Py output mandatory rather than allowing the native fallback:

```bash
python scripts/run_pm4py_discovery.py --require-pm4py
```

Process-discovery artifacts are written to `careflow_data/process_discovery/`. The runner exports a PM4Py directly-follows graph and a Petri-net PNML model when PM4Py is installed; the native pandas-based artifacts are still created if that optional import is unavailable.

## BigQuery + dbt next milestone

The next-stage implementation is documented in [`docs/WAREHOUSE_AND_PROCESS_MINING.md`](docs/WAREHOUSE_AND_PROCESS_MINING.md). It contains the full setup steps; the short version is:

1. Install the existing local requirements and then `pip install -r requirements-cloud.txt`.
2. Configure a Google Cloud project, enable BigQuery, and authenticate using an approved method.
3. Set `GCP_PROJECT_ID` and optionally `BIGQUERY_LOCATION`.
4. Load the synthetic data into a dedicated demo table:

   ```bash
   python scripts/load_synthetic_to_bigquery.py --dataset careflow_raw --table raw_event_log
   ```

   **Warning:** the script uses `WRITE_TRUNCATE` for the specified destination table. Use it only for the dedicated synthetic demo table. It refuses to upload rows unless every row is marked `Is_Synthetic=True`.

5. Copy `careflow_dbt/profiles.yml.example` to `~/.dbt/profiles.yml`, review the project and authentication values, then run:

   ```bash
   cd careflow_dbt
   dbt debug
   dbt run
   dbt test
   ```

The raw source defaults to `careflow_raw.raw_event_log`. With dbt's default custom-schema naming, models are placed in datasets such as `<target_dataset>_staging`, `<target_dataset>_intermediate`, and `<target_dataset>_marts`. The source dataset is configurable via `--vars`.

The marts include patient-case metrics, transition bottlenecks, X-Ray-to-Triage loopbacks, process variants, and exact-sequence conformance results. **Cloud load and dbt execution have not been run against an actual GCP project in this workspace** because no cloud project or credentials were provided. Run `dbt debug`, `dbt run`, and `dbt test` in your own configured environment before relying on these models.

## Core event-log schema

| Field | Meaning |
|---|---|
| `Case_ID` | Anonymous identifier for one simulated visit |
| `Activity_Name` | Activity performed, such as Triage or X-Ray |
| `Timestamp` | Timestamp of the event |
| `Department` | Simulated department responsible for the event |
| `Resource_ID` | Synthetic staff/resource identifier |
| `Age_Band` | Synthetic age band for cohort filtering |
| `Arrival_Shift` | Derived arrival-shift category |
| `Return_Reason` | Populated on the injected repeat-triage event |
| `Is_Synthetic` | Marks all records as synthetic |

The first three columns are the required basis for process mining. Additional fields exist for prototype analysis and should be reviewed/minimized before any real-data deployment.

## Metric definitions and caveats

- **Case throughput time** = last event timestamp minus first event timestamp in a case.
- **Inter-event elapsed time** = next event timestamp minus current event timestamp. Without queue-entry, activity-start, and activity-end timestamps, this is not pure waiting time or service time.
- **Triage-return rate** = cases with a direct `X-Ray → Triage` transition divided by all cases.
- **Baseline conformance** = exact sequence match against `Registration → Triage → Physician Assessment → X-Ray → Physician Reassessment → Treatment → Discharge`.
- **Process discovery** describes behavior recorded in the event log. A mined path is not automatically a clinically approved pathway.

## Responsible use and production gaps

Do not commit real patient data, credentials, tokens, or service-account keys to GitHub. Before using EHR records, obtain authorization and implement the healthcare organization's privacy, security, access-control, audit, and retention requirements. Define valid clinical alternatives with process owners before treating deviation rates as quality measures. Operational impact (for example, lower waiting time after a form change) must be evaluated against valid before/after operational data; the synthetic demo cannot establish that result.

## Remaining milestones

1. Configure and validate the BigQuery/dbt pipeline in an authorized cloud project.
2. Test PM4Py discovery and formal alignment-based conformance on the selected environment and clinically reviewed process definitions.
3. Build the Power BI/Looker dashboard with process flow, return-loop KPIs, bottleneck analysis, and controlled drill-down.
4. Replace synthetic events with authorized, de-identified data only after governance and source-schema approval.
