#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for Learning Path Recommender"
echo "=================================================================="

# Run decomposition #1 (Q1: All scenarios)
echo "Running Q1 decomposition (all_recommendation_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Expert with low competency)
echo "Running Q2 decomposition (expert_low_competency_recommended)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_expert_low_competency.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Competency dead zone safety)
echo "Running Q3 verification (competency dead zone safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_competency_dead_zone_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
