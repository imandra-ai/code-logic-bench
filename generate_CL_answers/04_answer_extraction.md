# Prompt: Answer Extraction

You are extracting answers from CodeLogician analysis results to create structured answers.

## Input

- `cl_analysis/*.json`: JSON output from decomposition and VG runs
- `questions.yaml`: Original questions
- `model.iml`: The IML model (for reference)

## Output

- `extract_cl_answers.sh`: Script using jq to extract answers
- `answer_CL.yaml`: Structured answers with reasoning

## Step 1: Understand JSON Output Structure

### Decomposition Output

```json
[{
  "regions_str": [
    {
      "constraints_str": "x >= 1 && y <= 0",
      "invariant_str": "\"positive\"",
      "model_str": {"x": 5, "y": -2},
      "model_eval_str": "\"positive\""
    },
    ...
  ]
}]
```

- `regions_str`: Array of all regions
- `constraints_str`: Conditions that define this region
- `invariant_str`: The output/result for this region
- `model_str`: A concrete example input
- `model_eval_str`: The output for the concrete example

### VG Output (Proved)

```json
[
  {
    "proved": {
      "proof": "..."
    }
  }
]
```

### VG Output (Refuted)

```json
[{
  "refuted": {
    "param1": 5,
    "param2": -3,
    ...
  }
}]
```

The `refuted` field provides a concrete counter-example input that violates the property.

## Step 2: Write jq Extraction Commands (Optional)

This step is optional and `jq` can be replaced with any other tool that can extract the desired information.

### For Enumeration Questions (Count Scenarios)

```bash
# Count total regions
jq '.[0].regions_str | length' decomp_file.json

# Get all distinct invariants (outcomes)
jq '[.[0].regions_str[].invariant_str] | unique' decomp_file.json
```

### For Conditional Questions (Can X happen when Y?)

```bash
# Filter regions where condition Y holds and X is true
jq '[.[0].regions_str[] | select(.model_str.field >= threshold and .invariant_str == "true")] | {
  answer: (if length > 0 then "YES" else "NO" end),
  count: length,
  example: (if length > 0 then .[0].model_str else null end)
}' decomp_file.json

# Find specific scenarios
jq '[.[0].regions_str[] | select(.invariant_str | contains("Emergency"))]' decomp_file.json
```

### For Property Questions (VG Results)

```bash
# Check if proved or refuted
jq 'if .[0].proved != null then "PROVEN" else "REFUTED" end' vg_file.json

# Get counterexample if refuted
jq '{
  result: (if .[0].proved != null then "PROVEN" else "REFUTED" end),
  counterexample: .[0].refuted
}' vg_file.json
```

###: Create `extract_cl_answers.sh` for Answer Presentation

Template:

```bash
#!/bin/bash

echo "=== Question 1: <summary> ==="
jq '<extraction_query>' cl_analysis/<file1>.json

echo ""
echo "=== Question 2: <summary> ==="
jq '<extraction_query>' cl_analysis/<file2>.json

echo ""
echo "=== Question 3: <summary> ==="
jq '<extraction_query>' cl_analysis/<file3>.json
```

## Step 4: Write answer_CL.yaml

Template:

```yaml
model: "<model_name>"

# To reproduce: ./cl_analysis.sh
# To extract: ./extract_cl_answers.sh

q1:
  question: "<full question text>"

  answer: "<concise answer>"

  # For enumeration: key thresholds discovered
  key_thresholds:
    param1: [value1, value2]
    param2: [value1, value2]

  metadata:
    extraction: 'jq "..." file.json'

q2:
  question: "<full question text>"

  answer: "<YES/NO - brief explanation>"

  explanation: "<detailed explanation>"

  # If YES, include example scenario
  example_scenario:
    param1: value
    param2: value
    result: "..."

  metadata:
    extraction: 'jq "..." file.json'

q3:
  question: "<full question text>"

  answer: "<PROVEN/REFUTED - brief explanation>"

  property: "<the formal property checked>"

  # If PROVEN
  why_holds: "<explanation of why property holds>"

  # If REFUTED
  counterexample:
    param1: value
    param2: value
  why_violated: "<step-by-step explanation of how counterexample violates property>"

  metadata:
    extraction: 'jq "..." file.json'

analysis_metadata:
  total_regions: <N>
  analysis_notes: "<any relevant notes>"
```

## Answer Writing Guidelines

### For Enumeration Answers

- State the exact count: "1,899 scenarios"
- List key thresholds that create distinctions
- Explain what creates the complexity (if notable)

### For Conditional Answers

- Lead with YES/NO
- Explain the conditions that make it possible/impossible
- Provide a concrete example if YES
- Explain why it's impossible if NO

### For Property Answers

- Lead with PROVEN/REFUTED
- State the property clearly
- If PROVEN: Explain why it holds structurally
- If REFUTED: Walk through the counterexample step-by-step

## Common jq Patterns Reference

| Purpose             | jq Pattern                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| Count regions       | `.[0].regions_str \| length`                                                                    |
| Filter by field     | `[.[0].regions_str[] \| select(.model_str.x >= 5)]`                                             |
| Filter by invariant | `[.[0].regions_str[] \| select(.invariant_str == "true")]`                                      |
| Check VG result     | `if .[0].proved != null then "PROVEN" else "REFUTED" end`                                       |
| Get counterexample  | `.[0].refuted`                                                                                  |
| Unique invariants   | `[.[0].regions_str[].invariant_str] \| unique`                                                  |
| Count by invariant  | `.[0].regions_str \| group_by(.invariant_str) \| map({key: .[0].invariant_str, count: length})` |

## Validation

1. Run `extract_cl_answers.sh` and verify output makes sense
2. Cross-check answers with the actual JSON data
3. Ensure `answer_CL.yaml` is valid YAML (proper indentation, quoting)
4. Verify metadata extraction commands are correct
