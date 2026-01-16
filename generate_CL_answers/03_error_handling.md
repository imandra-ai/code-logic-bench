# Prompt: Error Handling and Retry Strategies

When running `codelogician`, you may encounter errors. This guide covers how to handle them.

## Reference Documentation
- IML syntax and semantics: `iml_docs/iml_overview.md`
- Decomposition parameters: `iml_docs/guides/region-decomp/writing-decomp.md`
- Verification goals: `iml_docs/guides/verification-goal`

## Error Categories

### 1. IML Syntax/Type Errors

**Symptoms**: `Eval failed!` with error message

**Action**: Refer to `iml_docs/iml_overview.md` and `iml_docs/iml_api_reference/` for correct IML syntax and module signatures and fix the code accordingly.

### 2. Decomposition Timeout

**Symptoms**: Decomposition runs for very long time or times out

**Strategies (try in order)**:

1. **Add `~prune:true`**: Eliminates infeasible regions
   ```iml
   [@@decomp top ~prune:true ()]
   ```

2. **Add `~assuming` to restrict input ranges**:
   ```iml
   [@@decomp top ~prune:true
       ~assuming:(fun x y z ->
         x >= 0 && x <= 100 &&
         y >= 0 && y <= 100 &&
         z >= 0 && z <= 50
       ) ()]
   ```
   **Critical**: The `~assuming` function must have the **exact same parameters** (names and order) as the target function.

3. **Use `~basis` to keep helpers unexpanded**:
   ```iml
   [@@decomp top ~prune:true ~basis:[[%id complex_helper]] ()]
   ```

4. **Simplify the analysis**: If still too complex, consider analyzing subcomponents separately.

### 3. Mismatched ~assuming Signature

**Symptoms**: `TacticEvalErr` or parameter mismatch error

**Fix**: Ensure exact same parameter names and order as the target function:

```iml
(* WRONG - different param count *)
let is_valid x = x > 0
let process x y = x + y
[@@decomp top ~assuming:[%id is_valid] ()]

(* CORRECT - same params *)
let is_valid x y = x > 0 && y > 0
let process x y = x + y
[@@decomp top ~assuming:[%id is_valid] ()]
```

### 4. Incorrect ~basis Syntax

**Fix**: Use double brackets for the list:

```iml
(* WRONG *)
~basis:[%id func1; %id func2]

(* CORRECT *)
~basis:[[%id func1]; [%id func2]]
```

## Validation Commands

```bash
# Check syntax and types
codelogician eval check model.iml

# List what will be analyzed
codelogician eval list-decomp model.iml
codelogician eval list-vg model.iml

# Run specific analysis (useful for debugging)
codelogician eval check-decomp --index 1 model.iml
codelogician eval check-vg --index 1 model.iml
```
