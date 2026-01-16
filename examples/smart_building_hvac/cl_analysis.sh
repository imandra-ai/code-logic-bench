#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (hvac_control_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_hvac_control_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: emergency mode selection)
echo "Running Q2 decomposition (selects_emergency_mode)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_selects_emergency_mode.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: safety property)
echo "Running Q3 verification (fire alarm safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_fire_alarm_safety.json 2>&1
echo "Q3 verification complete"
echo ""
