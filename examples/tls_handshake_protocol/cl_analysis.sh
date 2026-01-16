#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification for TLS Handshake Protocol"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (handshake_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_handshake_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: successful without forward secrecy)
echo "Running Q2 decomposition (successful_without_forward_secrecy)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_no_forward_secrecy.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: safety property)
echo "Running Q3 verification (high security policy => forward secrecy)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_safety_property.json 2>&1
echo "Q3 verification complete"
echo ""

echo "Running extraction of answers"
echo "===================="


echo "---"
echo "End of analysis"


