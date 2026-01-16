#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for deep_space_nav_planning_system"
echo "===================="

echo "Running Q1 decomposition (trajectory_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_trajectory_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

echo "Running Q2 decomposition (triggers_aerobrake)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_aerobrake.json 2>&1
echo "Q2 decomposition complete"
echo ""

echo "Running Q3 verification (emergency safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_emergency_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
