# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
#     "pydantic-ai",
#     "pyyaml",
# ]
# ///
"""
Generate evaluation metrics comparing LLM answers to CodeLogician answers.

- deps: examples/*/answer_LLM.yaml, examples/*/answer_CL.yaml, examples/*/questions.yaml
- target: examples/*/metrics.yaml
"""

import argparse
import asyncio
import fcntl
import os
from datetime import datetime
from math import log2
from pathlib import Path
from typing import Any, Literal

import dotenv
import yaml
from pydantic import BaseModel, Field, computed_field
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from yaml import Dumper

dotenv.load_dotenv()
script_dir = Path(__file__).parent
examples_dir = script_dir / 'examples'

DEFAULT_ANSWER_MODELS: list[str] = [
    'anthropic/claude-opus-4.6',
    'anthropic/claude-opus-4.5',
    'anthropic/claude-sonnet-4.5',
    'openai/gpt-5.2',
    'google/gemini-3-pro-preview',
    'x-ai/grok-code-fast-1',
]

DEFAULT_EVAL_MODELS: list[str] = [
    'google/gemini-2.5-flash',
    'anthropic/claude-haiku-4.5',
    'openai/gpt-4o-mini',
    'x-ai/grok-4-fast',
]


def mk_model(model_name: str) -> OpenRouterModel:
    return OpenRouterModel(
        model_name,
        provider=OpenRouterProvider(api_key=os.environ['OPENROUTER_API_KEY']),
    )


# Yaml helpers
# ====================


def str_representer(dumper: Dumper, data: str):
    """Use literal block style for multiline strings."""
    if '\n' in data:
        data = '\n'.join(line.rstrip() for line in data.split('\n'))
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')  # pyright: ignore[reportUnknownMemberType]
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)  # pyright: ignore[reportUnknownMemberType]


yaml.add_representer(str, str_representer)


def append_to_yaml_atomic(file_path: Path, new_data: dict[str, Any]) -> None:
    """Atomically append data to a YAML file with file locking."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'a+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            content = f.read()
            data_list: list[dict[str, Any]] = yaml.safe_load(content) if content else []
            data_list.append(new_data)
            f.seek(0)
            f.truncate()
            yaml.dump(
                data_list,
                f,
                Dumper=Dumper,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# Metrics definition
# ====================


class StateSpaceEstimationAccuracy(BaseModel):
    """Ratio of LLM's estimated scenario count to actual region count from decomposition."""

    n_llm_estimated_scenarios: int | Literal['unknown'] = Field(
        description='Number of scenarios estimated by LLM, or "unknown" if cannot be extracted.'
    )
    n_decomposition_exact_scenarios: int = Field(
        description='Exact number of regions from decomposition'
    )
    reasoning: str = Field(
        description='Explain how you extracted n_llm_estimated_scenarios and found n_decomposition_exact_scenarios.'
    )

    @computed_field
    @property
    def score(self) -> float | Literal['unknown']:
        if self.n_llm_estimated_scenarios == 'unknown':
            return 'unknown'
        diff = abs(
            self.n_llm_estimated_scenarios - self.n_decomposition_exact_scenarios
        )
        if diff == 0:
            return 1.0
        return 1.0 - abs(log2(diff))


class OutcomePrecision(BaseModel):
    """Measures how precisely the LLM provides exact numeric distributions."""

    score: float = Field(
        description='Precision score for numeric distributions (0.0-1.0)',
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        description='Detailed explanation of how the score was determined'
    )


class DirectionAccuracy(BaseModel):
    """Whether the LLM reaches conclusions in the correct direction."""

    score: float = Field(
        description='Score for correctness of conclusions (0.0-1.0)', ge=0.0, le=1.0
    )
    reasoning: str = Field(
        description='Detailed explanation of the conclusion correctness'
    )


class CoverageCompleteness(BaseModel):
    """Proportion of actual decision scenarios found by the LLM."""

    score: float = Field(
        description='Score for coverage of decision scenarios (0.0-1.0)',
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        description='Explanation of which rubric was applied and how coverage was assessed'
    )


class ControlFlowUnderstanding(BaseModel):
    """Assess whether LLM captures the structure of branches, guards, overrides, and short-circuits."""

    precedence_of_conditions: Literal['correct', 'partial', 'incorrect'] = Field(
        description='Assessment of precedence understanding'
    )
    branching_structure: Literal['correct', 'partial', 'incorrect'] = Field(
        description='Assessment of branching structure understanding'
    )
    short_circuit_behavior: Literal['correct', 'partial', 'incorrect'] = Field(
        description='Assessment of short-circuit behavior understanding'
    )
    override_logic: Literal['correct', 'partial', 'incorrect'] = Field(
        description='Assessment of override logic understanding'
    )
    reasoning: str = Field(description='Explain each of the 4 assessments.')

    @computed_field
    @property
    def score(self) -> float:
        assessments = [
            self.precedence_of_conditions,
            self.branching_structure,
            self.short_circuit_behavior,
            self.override_logic,
        ]
        correct_count = sum(1 for a in assessments if a == 'correct')
        partial_count = sum(1 for a in assessments if a == 'partial')
        return (correct_count + 0.5 * partial_count) / 4


class EdgeCaseDetection(BaseModel):
    """How many rare or policy-violating edge cases the LLM finds."""

    edge_cases_found: list[str] = Field(
        description='List of edge cases identified by the LLM'
    )
    total_edge_cases: int = Field(
        description='Total number of edge cases in decomposition'
    )
    reasoning: str = Field(
        description='Explain which edge cases were found and which were missed.'
    )

    @computed_field
    @property
    def edge_case_count(self) -> int:
        return len(self.edge_cases_found)

    @computed_field
    @property
    def score(self) -> float:
        if self.total_edge_cases == 0:
            return 1.0
        return min(len(self.edge_cases_found) / self.total_edge_cases, 1.0)


class DecisionBoundaryClarity(BaseModel):
    """Whether the LLM identifies exact numeric thresholds for decisions."""

    thresholds_identified_by_llm: list[str] = Field(
        description='List of thresholds identified by LLM'
    )
    thresholds_from_decomp: list[str] = Field(
        description='List of all thresholds from decomposition'
    )
    reasoning: str = Field(
        description='Explain which thresholds were identified and which were missed.'
    )

    @computed_field
    @property
    def score(self) -> float:
        if len(self.thresholds_from_decomp) == 0:
            return 1.0
        return min(
            len(self.thresholds_identified_by_llm) / len(self.thresholds_from_decomp),
            1.0,
        )


class EvaluationResult(BaseModel):
    """Complete evaluation result comparing LLM answers vs ImandraX answers."""

    state_space_estimation_accuracy: StateSpaceEstimationAccuracy | None = Field(
        description="Accuracy of LLM's scenario count estimation"
    )
    control_flow_understanding: ControlFlowUnderstanding | None = Field(
        description="Assessment of LLM's control flow understanding"
    )
    edge_case_detection: EdgeCaseDetection | None = Field(
        description='How many edge cases the LLM identifies'
    )
    decision_boundary_clarity: DecisionBoundaryClarity | None = Field(
        description='How many numeric thresholds the LLM identifies'
    )
    outcome_precision: OutcomePrecision | None = Field(
        description='Precision of numeric distributions provided by the LLM'
    )
    direction_accuracy: DirectionAccuracy | None = Field(
        description='Correctness of conclusions reached by the LLM'
    )
    coverage_completeness: CoverageCompleteness | None = Field(
        description='Proportion of decision scenarios found by the LLM'
    )
    overall_summary: str = Field(
        description='High-level assessment summarizing strengths and weaknesses'
    )


# Core function
# ====================


async def eval_one_answer(
    example_dir: Path,
    answer_model_name: str,
    eval_model_name: str,
) -> None:
    """Evaluate one answer set from answer_LLM.yaml using one eval model."""
    print(
        f'Evaluating {answer_model_name} with {eval_model_name} in {example_dir.name}'
    )

    # Load questions
    questions_path = example_dir / 'questions.yaml'
    questions_yaml = yaml.safe_load(questions_path.read_text())
    questions_dict = questions_yaml['questions']
    questions = [questions_dict[f'q{i}'] for i in range(1, 4)]

    # Build context
    context_str = (
        f'Problem name: {questions_yaml["model"]}\n'
        f'Core logic: {questions_yaml["core_function"]}\n'
        f'Description: {questions_yaml["description"]}\n'
    )

    # Load LLM answers
    answer_llm_path = example_dir / 'answer_LLM.yaml'
    answer_llm_list: list[dict[str, Any]] = yaml.safe_load(answer_llm_path.read_text())

    # Find the answer set for the specified answer_model_name
    answer_llm_dict: dict[str, Any] | None = None
    for answer_set in answer_llm_list:
        if answer_set.get('model') == answer_model_name:
            answer_llm_dict = answer_set
            break
    if answer_llm_dict is None:
        raise ValueError(f'Answer for model {answer_model_name} not found')

    # Load ImandraX answers
    answer_cl_path = example_dir / 'answer_CL.yaml'
    answer_cl_dict = yaml.safe_load(answer_cl_path.read_text())

    def get_llm_answer(q_idx: int) -> str:
        a = answer_llm_dict[f'q{q_idx}']
        return f'Answer: {a["answer"]}\n\nReasoning: {a["reasoning"]}'

    def get_cl_answer(q_idx: int) -> str:
        a = answer_cl_dict[f'q{q_idx}']
        return '\n'.join(
            f'{k}: {v}' for k, v in a.items() if k not in ['question', 'metadata']
        )

    # Build prompts for each question
    prompt_template = """
You are evaluating the quality of LLM answer vs ImandraX answer for a question about a model.

CONTEXT:
{context_str}

QUESTION:
{question}

LLM ANSWER (without decomposition / verification):
{llm_answer}

IMANDRAX ANSWER (with decomposition / verification):
{cl_answer}

Compare the answers and evaluate using the metrics definitions provided.
Provide detailed reasoning for each metric.
"""

    agent = Agent(mk_model(eval_model_name), output_type=EvaluationResult)
    prompts = [
        prompt_template.format(
            context_str=context_str,
            question=questions[i],
            llm_answer=get_llm_answer(i + 1),
            cl_answer=get_cl_answer(i + 1),
        )
        for i in range(3)
    ]

    responses = await asyncio.gather(*[agent.run(prompt) for prompt in prompts])
    evaluation_results = [response.output for response in responses]

    # Build result
    result: dict[str, Any] = {
        'answer_model': answer_model_name,
        'eval_model': eval_model_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': {
            f'q{i}': evaluation_results[i - 1].model_dump() for i in range(1, 4)
        },
    }

    # Append to metrics.yaml
    metrics_path = example_dir / 'metrics.yaml'
    append_to_yaml_atomic(metrics_path, result)
    print(f'Done: {answer_model_name} with {eval_model_name} in {example_dir.name}')


# CLI helper
# ====================


def has_existing_evaluation(
    example_dir: Path,
    answer_model_name: str,
    eval_model_name: str,
) -> bool:
    """Check if a specific answer_model + eval_model combination already exists."""
    metrics_path = example_dir / 'metrics.yaml'
    if not metrics_path.exists():
        return False
    try:
        metrics_list: list[dict[str, Any]] = yaml.safe_load(metrics_path.read_text())
        return any(
            entry.get('answer_model') == answer_model_name
            and entry.get('eval_model') == eval_model_name
            for entry in metrics_list
        )
    except Exception:
        return False


def get_all_examples() -> list[Path]:
    """Get all example directories that have required files."""
    examples: list[Path] = []
    for d in sorted(examples_dir.iterdir()):
        if (
            d.is_dir()
            and (d / 'answer_LLM.yaml').exists()
            and (d / 'answer_CL.yaml').exists()
            and (d / 'questions.yaml').exists()
        ):
            examples.append(d)
    return examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate evaluation metrics comparing LLM answers to ImandraX answers',
    )
    parser.add_argument(
        'examples',
        nargs='*',
        help='Example names to process (directories in examples/)',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all examples',
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip evaluations that already exist in metrics.yaml',
    )
    parser.add_argument(
        '--answer-models',
        nargs='+',
        default=DEFAULT_ANSWER_MODELS,
        help=f'Answer models to evaluate (default: {DEFAULT_ANSWER_MODELS})',
    )
    parser.add_argument(
        '--eval-models',
        nargs='+',
        default=DEFAULT_EVAL_MODELS,
        help=f'Evaluation models to use (default: {DEFAULT_EVAL_MODELS})',
    )
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Stop on first error instead of continuing',
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Determine which examples to process
    if args.all:
        example_dirs = get_all_examples()
    elif args.examples:
        example_dirs = [examples_dir / name for name in args.examples]
        for d in example_dirs:
            if not d.exists():
                print(f'Error: Example not found: {d.name}')
                raise SystemExit(1)
    else:
        print('Error: Specify example names or use --all')
        raise SystemExit(1)

    if not example_dirs:
        print('No examples to process')
        return

    # Build list of tasks
    tasks: list[tuple[Path, str, str]] = []
    for example_dir in example_dirs:
        for answer_model in args.answer_models:
            for eval_model in args.eval_models:
                if args.skip_existing and has_existing_evaluation(
                    example_dir, answer_model, eval_model
                ):
                    continue
                tasks.append((example_dir, answer_model, eval_model))

    if not tasks:
        print('No evaluations to run (all existing)')
        return

    print(f'Running {len(tasks)} evaluations')

    async def safe_eval(example_dir: Path, answer_model: str, eval_model: str) -> None:
        try:
            await eval_one_answer(example_dir, answer_model, eval_model)
        except Exception as e:
            print(f'Error: {example_dir.name} {answer_model} {eval_model}: {e}')
            if args.fail_fast:
                raise

    if args.fail_fast:
        for example_dir, answer_model, eval_model in tasks:
            await eval_one_answer(example_dir, answer_model, eval_model)
    else:
        await asyncio.gather(*[safe_eval(d, a, e) for d, a, e in tasks])

    print('Done')


if __name__ == '__main__':
    asyncio.run(main())
