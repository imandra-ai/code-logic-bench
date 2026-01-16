#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

# Q1: Hazardous waste scenarios
echo "Running Q1 decomposition (hazardous_scenarios with ~assuming)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_hazardous.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Q2: Low fuel approval
echo "Running Q2 decomposition (approved_with_low_fuel)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_low_fuel.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Q3: Organic threshold property
echo "Running Q3 verification (Organic at threshold property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_threshold.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
