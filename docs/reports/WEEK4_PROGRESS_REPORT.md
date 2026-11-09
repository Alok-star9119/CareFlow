# CareFlow — Week 4 Progress Report

**Project:** Clinical Pathway Process Mining  
**Reporting period:** Week 4  
**Focus:** Baseline conformance checking and dashboard-ready drill-down summaries

## 1. Objective
Week 4 implements a transparent first-pass comparison between each recorded patient journey and a defined reference pathway. Deviations are flagged at case level, with summary outputs intended to support dashboard refinement and controlled drill-down.

## 2. Reference pathway
The prototype baseline is:

`Registration → Triage → Physician Assessment → X-Ray → Physician Reassessment → Treatment → Discharge`

A case conforms only when its timestamp-ordered activity sequence exactly matches this list. Additional activities, missing activities, or activities in a different order are flagged. This is a simple exact-sequence rule for the prototype; it is not formal alignment-based conformance checking and must not be treated as a clinically mandated pathway without review by authorized clinical process owners.

## 3. Work prepared
- Input checks for required columns, blank case/activity values, and invalid timestamps.
- Timestamp-ordered event traces grouped by Case_ID.
- Case-level conformance status, deviation flag, observed trace, deviation explanation, and case duration.
- Overall conformance/deviation rates and mean case duration.
- Optional cohort summaries by available Department, Resource_ID, Age_Band, and Arrival_Shift fields.
- CSV exports for case results and each available drill-down dimension, plus a JSON KPI summary.
- Automated tests for baseline matches, extra/missing activities, invalid timestamps, and missing drill-down fields.

## 4. Deliverables
| File | Purpose |
|---|---|
| `week4_conformance.py` | Reusable conformance analysis and exports |
| `tests/test_week4_conformance.py` | Automated Week 4 tests |
| `WEEK4_DAILY_COMMITS.md` | Seven-day implementation and commit plan |
| `WEEK4_PROGRESS_REPORT.md` | Week 4 progress report |

## 5. Test status
The dedicated Week 4 test suite passed **6 tests** in the development environment. Run the commands in the README on the target machine before committing or relying on generated outputs.

## 6. Remaining integration and dashboard work
This report does not claim that a live BigQuery/dbt pipeline or a published Power BI/Looker dashboard has been configured or verified. The generated CSV/JSON outputs are prepared for downstream use. Dashboard filters, visual interactions, and cloud execution must be implemented and verified in the target environment. PM4Py alignment-based conformance can be considered after the chosen model and approved pathway variants are validated.

## 7. Data and interpretation limitations
The supplied demonstration data is synthetic. Its metrics are for software testing and must not be presented as real hospital performance evidence. The exact-match baseline flags any extra event as a deviation, including potentially legitimate clinical alternatives. Before using real records or interpreting deviations as quality measures, obtain authorization, de-identify data, and agree on valid pathway variants with clinical process owners.

## 8. Next steps
1. Review baseline and permitted pathway variants with relevant process owners.
2. Run the pipeline against approved, de-identified data only when authorized.
3. Verify CSV/JSON KPI values against dashboard calculations.
4. Configure and test dashboard drill-downs and cloud integrations.
5. Consider formal PM4Py alignment-based conformance and document its assumptions.

## Conclusion
Week 4 prepares a reproducible local workflow for comparing observed traces with a reference journey and exporting conformance metrics for BI exploration. Dedicated tests pass; cloud integration and dashboard publication remain verification tasks.
