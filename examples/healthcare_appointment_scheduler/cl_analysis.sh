#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for Healthcare Appointment Scheduler"
echo "=========================================================================="

# Run decomposition #1 (Q1: All scenarios)
echo "Running Q1 decomposition (all_scheduling_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Routine with pending insurance)
echo "Running Q2 decomposition (routine_with_pending_insurance)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_routine_pending.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Emergency with high no-shows)
echo "Running Q3 verification (emergency no-show safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_emergency_noshow_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
