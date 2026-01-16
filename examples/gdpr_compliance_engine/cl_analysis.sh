#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: scenario enumeration)
echo "Running Q1 decomposition (compliance_scenarios)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_compliance_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: LegalObligation rejections)
echo "Running Q2 decomposition (legal_obligation_rejected)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_legal_obligation_rejected.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: critical requires DPO)
echo "Running Q3 verification (critical requires DPO)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_critical_dpo.json 2>&1
echo "Q3 verification complete"
echo ""
