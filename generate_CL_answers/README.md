# CodeLogician Answer Generation Prompts

This directory contains reusable prompts for generating [CodeLogician](https://codelogician.dev/) answers from Python models. These prompts can be used with any agent framework or terminal agent.

`codelogician` CLI can be downloaded from [PyPI](https://pypi.org/project/codelogician/).

## Overview

The prompts guide an agent through generating formal analysis answers using CodeLogician:

```
Input: questions.yaml, model.py, iml_docs/
  ↓
Output: model.iml, cl_analysis.sh, answer_CL.yaml
```

## Prompts

| Prompt | Purpose |
|--------|---------|
| `01_python_to_iml.md` | Translate Python model to IML |
| `02_analysis_setup.md` | Analyze questions and write decomposition/VG |
| `03_error_handling.md` | Handle errors and retry strategies |
| `04_answer_extraction.md` | Extract answers from JSON results |
| `05_script_generation.md` | Generate cl_analysis.sh script |

## Workflow

1. **Translate** (`01`): Specify model using IML in `model.iml`
2. **Setup Analysis** (`02`): Add decomposition/VG to answer questions
3. **Generate Script** (`05`): Create `cl_analysis.sh`
4. **Run Analysis**: Execute `./cl_analysis.sh`
5. **Handle Errors** (`03`): Fix issues if analysis fails
6. **Extract Answers** (`04`): Create `extract_cl_answers.sh` (optional) and `answer_CL.yaml`

## Usage

### With Terminal Coding Agent (Claude Code, Codex, Gemini CLI, etc.)

Point the agent to the prompts and input files:

```
Read the prompts in generate_CL_answers/prompts/ and use them to:
1. Translate examples/my_example/model.py to model.iml
2. Add analysis to answer the questions in questions.yaml
3. Run the analysis and extract answers

Reference iml_docs/ for IML syntax and semantics.
```

### With Agent SDK (pydantic-ai, langchain, etc.)

Load each prompt file as a system prompt or instruction for your agent. Structure your pipeline with one agent/node per phase, passing outputs between phases.

The prompts are designed to be self-contained - each describes its inputs, outputs, and references to `iml_docs/` for additional context.

### Manual Step-by-Step

You can also use the prompts manually:

1. Read `01_python_to_iml.md`, then translate the Python model
2. Run `codelogician-tools eval check model.iml` to validate
3. Read `02_analysis_setup.md`, then add analysis code
4. Read `05_script_generation.md`, then create `cl_analysis.sh`
5. Run `./cl_analysis.sh`
6. If errors, consult `03_error_handling.md`
7. Read `04_answer_extraction.md`, then extract answers

## Dependencies

- `codelogician` CLI
- Optional:`jq` or other tools for extracting information from JSON
- `iml_docs/` directory for reference, which can be obtained from `codelogician doc dump` command.
