#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: GracePeriod billing scenarios)
echo "Running Q1 decomposition (grace_period_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_grace_period_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Can Basic tier get FullyApproved in GracePeriod?)
echo "Running Q2 decomposition (basic_grace_fully_approved)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_basic_grace_fully_approved.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Does Enterprise+Current always succeed?)
echo "Running Q3 verification (Enterprise Current billing property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_enterprise_current_property.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
echo "===================="
