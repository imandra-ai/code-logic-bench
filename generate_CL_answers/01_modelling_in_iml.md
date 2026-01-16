# Prompt: Python to IML Translation

You are translating a Python model to IML (Imandra Modeling Language). IML is a pure subset of OCaml used for formal verification.

## Reference Documentation
- **IML basics and syntax**: `iml_docs/iml_overview.md`
- **API reference**: `iml_docs/iml_api_reference/` - Module signatures for List, Option, etc.

## Input
- `model.py`: Python source code defining the model
- `questions.yaml`: Contains model name, core function, and questions to answer

## Output
- `model.iml`: Equivalent IML code (model definition section only, NOT the analysis section)

## Translation Approach

1. **Read `iml_docs/iml_overview.md`** for:
   - Type definitions (enums → variants, dataclasses → records)
   - Function syntax and pattern matching
   - Key differences from Python/OCaml (no exceptions, option types, etc.)

2. **Translate incrementally**:
   - Start with type definitions
   - Then helper functions
   - Finally the core function

3. **Translation tips** (see iml_docs for details):
   - Enums become variant types: `type status = Active | Inactive`
   - Dataclasses become records: `type result = { value: int; valid: bool }`
   - No exceptions - use `Option` to define total functions
   - `real` for decimals (not `float`), use `Real.of_int` for conversion

## Validation

After translation, verify the code compiles:

```bash
codelogician eval check model.iml
```

Expected output: `Eval success!`

If there are errors, refer to `iml_docs/` for correct syntax and fix accordingly.
