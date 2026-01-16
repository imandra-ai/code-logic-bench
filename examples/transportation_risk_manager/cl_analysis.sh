#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: Sea under tensions)
echo "Running Q1 decomposition (sea_under_tensions with ~assuming)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_sea_under_tensions.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Air rejected for Standard)
echo "Running Q2 decomposition (air_rejected_non_hazardous)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_air_rejected.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Air emergency property)
echo "Running Q3 verification (Air emergency routing property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_air_emergency.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
