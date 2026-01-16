# Prompt: Analysis Setup (Decomposition & Verification Goals)

You are adding analysis code to an IML model to answer questions. You must analyze each question to determine whether to use **region decomposition** or **verification goals (VG)**.

## Reference Documentation

- Region decomposition: `iml_docs/guides/region-decomp/`
  - Quick start: `iml_docs/guides/region-decomp/quick-start.md`
  - Writing decomp: `iml_docs/guides/region-decomp/writing-decomp.md`
  - Strategic guide: `iml_docs/guides/region-decomp/how-to-use-decomp-for-analysis.md`
- Verification goals: `iml_docs/guides/verification-goal/quick-start.md`

## Input

- `model.iml`: The IML model (translation from Python)
- `questions.yaml`: Questions to answer about the model

## Output

- Updated `model.iml` with Analysis section containing decomposition requests and/or verification goals

## Step 1: Analyze Each Question

For each question, determine its appropriate analysis type:

| Question Pattern                        | Type        | Use                       |
| --------------------------------------- | ----------- | ------------------------- |
| "How many scenarios/cases/paths exist?" | Enumeration | Region Decomposition      |
| "What are ALL the ways X can happen?"   | Exhaustive  | Region Decomposition      |
| "Under what conditions does X occur?"   | Conditional | Region Decomposition      |
| "Can X ever happen when Y?"             | Conditional | Region Decomposition / VG |
| "Does property X always hold?"          | Property    | VG                        |
| "Can property X ever be violated?"      | Property    | VG                        |
| "Is it always true that...?"            | Property    | VG                        |

## Step 2: Write Analysis Code

### For Enumeration Questions

Use basic decomposition on the core function:

```iml
(* Question: How many distinct scenarios exist? *)
let scenario_analysis = <core_function>
[@@decomp top ~prune:true ()]
```

- `~prune:true` removes infeasible regions (recommended)
- Count regions with: `jq '.[0].regions_str | length'`

### For Conditional Questions

Option 1: Create a wrapper function that returns the condition of interest:

```iml
(* Question: Can X ever happen when Y? *)
let when_condition_occurs param1 param2 ... =
  let result = <core_function> param1 param2 ... in
  result.<field_of_interest>  (* or a boolean expression *)
[@@decomp top ()]
```

Option 2: use `~assuming` to restrict state space

Then filter results with jq to find regions where the condition holds.

### For Property Questions

Use `verify` with the property as an implication:

```iml
(* Question: Does property "X implies Y" always hold? *)
verify (fun param1 param2 ... ->
  let result = <core_function> param1 param2 ... in
  <precondition> ==> <postcondition>
)
```

Common property patterns:

- "X always implies Y": `X ==> Y`
- "When X is true, Y must be true": `X ==> Y`
- "X can never happen": `not X`

### For Large State Spaces

If the model has many parameters, add `~assuming` to restrict input ranges:

```iml
let scenario_analysis = <core_function>
[@@decomp top ~prune:true
    ~assuming:(fun param1 param2 ... ->
      param1 >= 0 && param1 <= 100 &&
      param2 >= 0 && param2 <= 1000
    ) ()]
```

**Critical**: The `~assuming` function must have the **exact same parameters** as the target function.

## Step 3: Verify Analysis Code

After adding analysis, verify the file still compiles:

```bash
codelogician eval check model.iml
```

List decompositions and VGs:

```bash
codelogician eval list-decomp model.iml
codelogician eval list-vg model.iml
```

## Output Checklist

- [ ] Each question has corresponding analysis code
- [ ] Decomposition uses appropriate parameters (~prune, ~assuming)
- [ ] VG uses correct implication structure (precondition ==> postcondition)
- [ ] File passes `codelogician-tools eval check-vg` and `codelogician eval check-decomp`
