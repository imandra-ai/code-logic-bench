#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (infusion_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_infusion_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: critical hardware allowed)
echo "Running Q2 decomposition (critical_hardware_allowed)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_critical_hardware.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run decomposition #3 (Q3: high risk no double check)
echo "Running Q3 decomposition (high_risk_no_double_check)..."
codelogician-tools eval check-decomp --index 3 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q3_double_check.json 2>&1
echo "Q3 decomposition complete"
echo ""
