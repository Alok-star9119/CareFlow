# Week 3 daily GitHub commit plan

Each day includes a meaningful code/documentation task and a commit message longer than 60 characters. Do not make empty commits: complete the task, run the relevant test, then commit.

Day 1 — Add normalized event-log validation and clear error messages.
Commit: `Week 3 Day 1: validate event-log columns, timestamps, blank IDs, and activity names`

Day 2 — Calculate transition counts and elapsed time in minutes.
Commit: `Week 3 Day 2: calculate transition counts and mean, median, and P90 wait times`

Day 3 — Add case duration and X-Ray-to-Triage loopback indicators.
Commit: `Week 3 Day 3: add case throughput duration and case-level loopback detection`

Day 4 — Create shift-level summary when Arrival_Shift exists.
Commit: `Week 3 Day 4: summarize case durations and loopback rates by arrival shift`

Day 5 — Export dashboard-ready CSV files and JSON KPI summary.
Commit: `Week 3 Day 5: export bottleneck, case, shift, and KPI summaries for BI dashboards`

Day 6 — Add automated tests for valid metrics and invalid input.
Commit: `Week 3 Day 6: test transition timings, loopbacks, invalid timestamps, and missing columns`

Day 7 — Document run instructions, output fields, and synthetic-data limitations.
Commit: `Week 3 Day 7: document analytics workflow, output files, tests, and data limitations`

Useful commands:
```bash
git status
python -m pytest tests -q
git add week3_bottleneck_metrics.py tests/test_week3_bottleneck_metrics.py README_week3.md WEEK3_DAILY_COMMITS.md
git commit -m "Week 3 Day 1: validate event-log columns, timestamps, blank IDs, and activity names"
git push
```
Change the commit message each day to match the work actually completed. Commit messages are not a substitute for real code changes.
