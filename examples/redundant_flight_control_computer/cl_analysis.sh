#!/bin/bash
set -e

mkdir -p cl_analysis
M="model.iml"
codelogician-tools eval check-decomp --index 1 --json $M > cl_analysis/decomp_q1.json 2>&1
codelogician-tools eval check-decomp --index 2 --json $M > cl_analysis/decomp_q2.json 2>&1
codelogician-tools eval check-decomp --index 3 --json $M > cl_analysis/decomp_q3.json 2>&1
echo "Done"
