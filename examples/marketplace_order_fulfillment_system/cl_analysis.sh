#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running decomposition and verification for Marketplace Order Fulfillment"
echo "======================================================================"

# Run decomposition #1 (Q1: All scenarios)
echo "Running Q1 decomposition (all_fulfillment_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_all_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Express Rural Food)
echo "Running Q2 decomposition (express_rural_food)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_express_rural_food.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Inventory dead zone safety)
echo "Running Q3 verification (inventory dead zone safety property)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_inventory_dead_zone_safety.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"
