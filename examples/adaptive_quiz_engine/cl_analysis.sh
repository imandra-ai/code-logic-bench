#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (progression_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_progression_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: emergency reset triggers)
echo "Running Q2 decomposition (triggers_emergency_reset)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_emergency_reset.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: safety property)
echo "Running Q3 verification (emergency reset safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_emergency_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
