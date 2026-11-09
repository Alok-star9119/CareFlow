# Power BI / Looker Studio Build Guide

The repository ships a ready-to-open HTML dashboard (`dashboard/careflow_dashboard.html`). To build the
enterprise version in Power BI or Looker Studio, follow the steps below. A `.pbix` file cannot be generated
outside Power BI Desktop, so this guide gives the exact data model and measures.

## 1. Connect to data
**Power BI Desktop → Get Data → Google BigQuery** (after `dbt run`), choose the mart tables below. For an
offline demo use **Get Data → Text/CSV** with the files in `careflow_data/`.

| Table | BigQuery mart | CSV fallback |
|---|---|---|
| Cases | `fct_patient_cases` | `careflow_data/case_metrics.csv` |
| Transitions | `fct_transition_bottlenecks` | `careflow_data/transition_bottlenecks.csv` |
| Loopbacks | `fct_triage_loopbacks` | `careflow_data/week3_metrics/week3_case_metrics.csv` |
| Variants | `fct_process_variants` | `careflow_data/process_variants.csv` |
| Conformance | `fct_conformance_results` | `careflow_data/week4_outputs/week4_conformance_by_case.csv` |
| Events (for the process visual) | `stg_careflow__events` | `careflow_data/clean_event_log.csv` |

Relate `Cases[Case_ID]` 1-to-many to `Conformance[Case_ID]` and `Events[Case_ID]`.

## 2. Process-map visual
Install a process-mining custom visual from AppSource (for example *Process Mining by Celonis* or the
*Power Automate Process Mining* visual). Map `Case_ID`, `Activity_Name`, `Timestamp` from `Events`.
Alternative: *Dynamic Network Graph* using `Transitions[Activity_Name]` → `Transitions[Next_Activity]`
with `Transition_Count` as edge weight.

## 3. DAX measures
```DAX
Total Cases        = DISTINCTCOUNT ( Cases[Case_ID] )
Avg Case Minutes   = AVERAGE ( Cases[Case_Duration_Minutes] )
Loopback Cases     = CALCULATE ( [Total Cases], Cases[Returned_To_Triage_After_XRay] = TRUE () )
Loopback Rate %    = DIVIDE ( [Loopback Cases], [Total Cases] ) * 100
Conforming Cases   = CALCULATE ( DISTINCTCOUNT ( Conformance[Case_ID] ), Conformance[Conforms_To_Baseline] = TRUE () )
Conformance Rate % = DIVIDE ( [Conforming Cases], [Total Cases] ) * 100
Avg Minutes Looped = CALCULATE ( [Avg Case Minutes], Cases[Returned_To_Triage_After_XRay] = TRUE () )
Avg Minutes Clean  = CALCULATE ( [Avg Case Minutes], Cases[Returned_To_Triage_After_XRay] = FALSE () )
Potential Savings (min) = ( [Avg Minutes Looped] - [Avg Minutes Clean] ) * DIVIDE ( [Loopback Cases], [Total Cases] )
```

## 4. Page layout
1. **KPI cards:** Total Cases, Avg Case Minutes, Loopback Rate %, Conformance Rate %, Potential Savings.
2. **Process map** (centre) filtered by slicers.
3. **Bar chart:** `Mean_Elapsed_Minutes` by `Transition` (sorted descending) — the bottleneck view.
4. **Table:** variants with case count and share.
5. **Slicers (drill-down):** `Age_Band`, `Arrival_Shift`, `Department`, `Resource_ID` (physician).
6. **Drill-through page:** right-click a variant → case list with `Observed_Trace` and `Deviation_Detail`.

## 5. Looker Studio
Use the BigQuery connector on the same marts, create the same scorecards, a bar chart for transitions,
and add filter controls for age band, shift and resource. Looker Studio has no native process-map; embed
the HTML dashboard or use a community visualization.

> All figures come from synthetic data. Cloud/BI steps must be run and validated in your own environment.
