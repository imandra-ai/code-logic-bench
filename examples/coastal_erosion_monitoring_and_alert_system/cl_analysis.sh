#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for coastal_erosion_monitoring_and_alert_system"
echo "===================="

echo "Running Q1 decomposition (alert_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_alert_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (triggers_evacuation)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_evacuation.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (failed sensor safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_failed_sensor.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
