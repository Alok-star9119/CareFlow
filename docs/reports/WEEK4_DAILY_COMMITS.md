# CareFlow Week 4 — 7-day implementation and GitHub commit plan

Week 4 follows the project brief: compare each observed patient journey with a defined reference journey, flag deviations, and prepare dashboard drill-down summaries. The baseline is a prototype exact-sequence rule, not a clinically approved care standard.

## Day 1 — Define the reference pathway and validate inputs
Task: document the baseline activity sequence and validate required event-log columns and timestamps.
Commit: `Week 4 Day 1: define reference pathway and validate event-log inputs before conformance checks`

## Day 2 — Build ordered case traces
Task: sort each case by timestamp and create one ordered activity trace per Case_ID.
Commit: `Week 4 Day 2: build timestamp-ordered patient traces for pathway comparison`

## Day 3 — Flag conformance deviations
Task: compare each trace against the reference pathway and record case-level match status and readable deviation details.
Commit: `Week 4 Day 3: flag nonconforming patient traces and explain sequence deviations`

## Day 4 — Add dashboard drill-down summaries
Task: summarize conformance, deviation rate, and case duration by available Department, Resource_ID, Age_Band, and Arrival_Shift fields.
Commit: `Week 4 Day 4: add conformance drill-down summaries by department resource age band and shift`

## Day 5 — Export BI-ready outputs
Task: export per-case conformance CSV, overall and grouped summary CSVs, and a JSON KPI summary.
Commit: `Week 4 Day 5: export case-level conformance results and dashboard-ready KPI summaries`

## Day 6 — Test conformance and edge cases
Task: run automated tests for conforming traces, extra/missing activities, invalid timestamps, and missing drill-down fields.
Commit: `Week 4 Day 6: test pathway matches deviations timestamps and cohort drill-down validation`

## Day 7 — Document, review, and report
Task: document commands, output definitions, baseline limitations, synthetic-data caveats, and remaining cloud/BI work.
Commit: `Week 4 Day 7: document conformance workflow outputs limitations and Week 4 progress`

## Commands

```bash
python -m pytest tests/test_week4_conformance.py -q
python week4_conformance.py --input careflow_data/clean_event_log.csv --output-dir careflow_data/week4_outputs
git status
git add WEEK4_DAILY_COMMITS.md WEEK4_PROGRESS_REPORT.md week4_conformance.py tests/test_week4_conformance.py README.md
# Use only the commit message for the day whose task you actually completed.
git commit -m "Week 4 Day 1: define reference pathway and validate event-log inputs before conformance checks"
git push
```

Do not make empty commits. Change the commit message each day to match the actual task completed. Do not claim BigQuery/dbt/PM4Py/Power BI/Looker integration is complete unless it has been run and verified in the configured environment.
