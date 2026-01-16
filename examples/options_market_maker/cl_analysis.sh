#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

echo "Running Q1 decomposition (all_quote_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_quotes.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (quote_exceeds_delta)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_delta_exceeded.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (Extreme vol + expiry)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_extreme_risk.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
