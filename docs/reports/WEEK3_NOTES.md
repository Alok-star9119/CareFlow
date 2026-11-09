# CareFlow — Week 3 Analytics Update

## Purpose
Week 3 adds bottleneck and throughput metrics that can be used in a Power BI or Looker dashboard. The code works on a normalized event log and exports dashboard-ready CSV files.

## New file
- `week3_bottleneck_metrics.py` — validates the input, calculates consecutive transition wait times, summarizes case duration, flags X-Ray → Triage loopbacks, and exports a JSON KPI summary.

## Run
From the CareFlow project root, with pandas installed:

```bash
python week3_bottleneck_metrics.py --input careflow_data/clean_event_log.csv --output-dir careflow_data/week3_metrics
```

The input CSV must contain `Case_ID`, `Activity_Name`, and `Timestamp`. `Arrival_Shift` is optional and enables the shift-level summary.

## Outputs
- `week3_transition_bottlenecks.csv`: transition count, mean, median, and 90th-percentile wait time.
- `week3_case_metrics.csv`: case duration, event count, trace, and X-Ray-to-Triage loopback flag.
- `week3_shift_metrics.csv`: case duration and loopback rate by arrival shift when available.
- `week3_kpi_summary.json`: high-level counts and summary metrics.

## Test
Run from this folder:

```bash
python -m pytest tests -q
```

## Interpretation and limitations
The project data is synthetic. Results are for demonstrating an analytics workflow and are not real hospital performance findings. The current implementation is local Python/pandas work; BigQuery, dbt, PM4Py execution, and dashboard publication should only be marked complete after they have actually been run and verified.
