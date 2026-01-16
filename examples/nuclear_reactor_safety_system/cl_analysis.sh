#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification for nuclear reactor safety system"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (response_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_response_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: SCRAM triggers)
echo "Running Q2 decomposition (triggers_scram)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_triggers_scram.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: safety property)
echo "Running Q3 verification (critical temperature safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_critical_temp_scram.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analyses complete!"
echo "Results saved:"
echo "  - decomp_q1_response_scenarios.json"
echo "  - decomp_q2_triggers_scram.json"
echo "  - vg_q3_critical_temp_scram.json"
