#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"
TIMEOUT=600000  # 10 minutes

echo "Running decomposition and verification"
echo "===================="

# Run decomposition #1 (Q1: RivalFaction scenarios with ~assuming)
echo "Running Q1 decomposition (rival_faction_scenarios with ~assuming)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q1_rival_faction_scenarios.json 2>&1
echo "Q1 decomposition complete"
echo ""

# Run decomposition #2 (Q2: Can HostileEmpire offer FetchQuests?)
echo "Running Q2 decomposition (hostile_empire_fetch)..."
codelogician-tools eval check-decomp --index 2 --json "$MODEL_FILE" \
  > cl_analysis/decomp_q2_hostile_empire_fetch.json 2>&1
echo "Q2 decomposition complete"
echo ""

# Run verification (Q3: Does high reputation always enable HiddenQuestline?)
echo "Running Q3 verification (hidden questline property - expecting REFUTED)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_q3_hidden_questline_property.json 2>&1
echo "Q3 verification complete"
echo ""

echo "All analysis complete!"
echo "===================="
