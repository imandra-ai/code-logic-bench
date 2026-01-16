#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for autonomous_tractor_fleet_coordination"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (assignment_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_assignment_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: emergency brake triggers)
echo "Running Q2 decomposition (triggers_spraying_in_rain)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_spraying_in_rain.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: emergency override safety property)
echo "Running Q3 verification (emergency override property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_collision_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
