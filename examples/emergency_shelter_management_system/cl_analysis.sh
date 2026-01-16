#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

echo "Running Q1 decomposition (assignment_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_assignment_scenarios.json 2>&1
echo "Q1 complete"

echo "Running Q2 decomposition (critical_medical_rejected)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_critical_medical_rejected.json 2>&1
echo "Q2 complete"

echo "Running Q3 verification (extreme_critical_safety)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_extreme_critical_safety.json 2>&1
echo "Q3 complete"
