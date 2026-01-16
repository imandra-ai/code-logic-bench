#!/bin/bash
set -e

mkdir -p cl_analysis
echo "Running analysis..."
codelogician-tools eval check-decomp --index 1 --json model.iml > cl_analysis/decomp_q1.json 2>&1
codelogician-tools eval check-decomp --index 2 --json model.iml > cl_analysis/decomp_q2.json 2>&1
codelogician-tools eval check-vg --index 1 --json model.iml > cl_analysis/vg_q3.json 2>&1
echo "Done"
