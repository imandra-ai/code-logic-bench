#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

echo "Running Q1 decomposition (photolithography_scenarios with ~assuming)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_photolithography.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (approved_class100)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_class100.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (Critical override property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_critical_override.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
