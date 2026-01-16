#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

echo "Running Q1 decomposition (all_auth_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_auth.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (granted_no_totp)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_no_totp.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (Lockout at max attempts)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_lockout.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
