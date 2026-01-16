#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for distributed_virtual_power_controller"
echo "===================="

echo "Running Q1 decomposition (dispatch_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_dispatch_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (triggers_discharge)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_discharge.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (emergency discharge property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_emergency_discharge.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
