#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition"
echo "===================="

echo "Q1: fraud_scenarios..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" > cl_analysis/decomp_q1_scenarios.json 2>&1
echo "Q1 complete"

echo "Q2: casino_allowed..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" > cl_analysis/decomp_q2_casino.json 2>&1
echo "Q2 complete"

echo "Q3: large_amount_no_review..."
codelogician-tools eval check-decomp --index 3 --json "$MODEL_FILE" > cl_analysis/decomp_q3_large_amount.json 2>&1
echo "Q3 complete"
