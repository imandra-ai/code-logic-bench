# Prompt: Script Generation (cl_analysis.sh)

You are generating a bash script to run CodeLogician analysis on an IML model.

## Input

- `model.iml`: The IML model with analysis section (decompositions and VGs)

## Output

- `cl_analysis.sh`: Bash script that runs all decompositions and VGs, saving results to JSON

## Step 1: List Analysis Targets

First, identify what needs to be run:

```bash
# List decompositions
codelogician eval list-decomp model.iml

# List verification goals
codelogician eval list-vg model.iml
```

This tells you how many decompositions and VGs exist and their indices.

## Step 2: Generate Script

Template:

```bash
#!/bin/bash
set -e

mkdir -p cl_analysis

MODEL_FILE="model.iml"

echo "Running CodeLogician analysis"
echo "===================="

# For each decomposition (index starts at 1)
echo "Running decomposition #1 (<description>)..."
codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
  > cl_analysis/decomp_<name>.json 2>&1
echo "Decomposition #1 complete"
echo ""

# Repeat for additional decompositions...

# For each verification goal (index starts at 1)
echo "Running verification goal #1 (<description>)..."
codelogician-tools eval check-vg --index 1 --json "$MODEL_FILE" \
  > cl_analysis/vg_<name>.json 2>&1
echo "Verification goal #1 complete"
echo ""

# Repeat for additional VGs...

echo "---"
echo "Analysis complete"
```

## Notes and Tips

1. **Indices start at 1**: The `--index` parameter uses 1-based indexing
2. **Order matters**: Decompositions and VGs are indexed in the order they appear in the file
3. **Redirect stderr**: Use `2>&1` to capture any error messages in the JSON file
4. **set -e**: Script exits on first error - remove if you want to continue despite failures
5. **Long-running analysis**: Some decompositions can take minutes. Add timeouts if needed:
   ```bash
   timeout 300 codelogician-tools eval check-decomp --index 1 --json "$MODEL_FILE" \
     > cl_analysis/decomp_scenarios.json 2>&1 || echo "Timeout or error"
   ```
