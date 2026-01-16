#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

echo "Running Q1 decomposition (highspeed_scenarios with ~assuming)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_highspeed.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (production_at_critical)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_critical_safety.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (Emergency stop guarantee)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_emergency_stop.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
