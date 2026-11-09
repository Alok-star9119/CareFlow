#!/usr/bin/env bash
# Reproduce every local artifact end-to-end (synthetic data). Run from the repository root.
set -euo pipefail
python scripts/audit_event_log.py
python scripts/run_pm4py_discovery.py
python scripts/week3_bottleneck_metrics.py --input careflow_data/clean_event_log.csv --output-dir careflow_data/week3_metrics
python scripts/week4_conformance.py --input careflow_data/clean_event_log.csv --output-dir careflow_data/week4_outputs
python scripts/run_pm4py_conformance.py
python scripts/build_dashboard.py
python -m pytest tests -q
