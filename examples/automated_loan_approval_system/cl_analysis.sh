#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (approval_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_approval_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: excellent credit manual review)
echo "Running Q2 decomposition (excellent_requires_manual)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_excellent_manual.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: safety property)
echo "Running Q3 verification (manual review safety)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_manual_review_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
