#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for Multi-Agency Emergency Dispatch"
echo "========================================================================"

# Run decomposition #1 (Q1: All scenarios)
echo "Running Q1 decomposition (all_dispatch_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Helicopter in storm)
echo "Running Q2 decomposition (helicopter_storm_dispatch)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_helicopter_storm.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Fuel dead zone backup requirement)
echo "Running Q3 verification (fuel dead zone backup safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_fuel_dead_zone_backup.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
