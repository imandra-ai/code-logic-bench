# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
#     "pyyaml",
#     "pydantic",
#     "pydantic-ai",
# ]
# ///
"""
Generate LLM answers for examples using multiple models.

Asks LLM models to answer questions given Python model definitions.

- deps: examples/*/questions.yaml, examples/*/model.py
- target: examples/*/answer_LLM.yaml
"""

import argparse
import asyncio
import fcntl
import os
from datetime import datetime
from pathlib import Path

import dotenv
import yaml
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from yaml import Dumper

dotenv.load_dotenv()
script_dir = Path(__file__).parent
examples_dir = script_dir / 'examples'


class Answers(BaseModel):
    q1_answer: str = Field(description='Answer to question 1')
    q1_reasoning: str = Field(
        description='Reasoning for answer to question 1 in bullet points'
    )
    q2_answer: str = Field(description='Answer to question 2')
    q2_reasoning: str = Field(
        description='Reasoning for answer to question 2 in bullet points'
    )
    q3_answer: str = Field(description='Answer to question 3')
    q3_reasoning: str = Field(
        description='Reasoning for answer to question 3 in bullet points'
    )


DEFAULT_MODELS: list[str] = [
    'anthropic/claude-opus-4.5',
    'anthropic/claude-sonnet-4',
    'openai/gpt-5.2',
    'google/gemini-3-pro-preview',
    'x-ai/grok-code-fast-1',
]


def mk_model(model_name: str) -> OpenRouterModel:
    return OpenRouterModel(
        model_name,
        provider=OpenRouterProvider(api_key=os.environ['OPENROUTER_API_KEY']),
    )


# YAML helpers
# ====================


def str_representer(dumper: Dumper, data: str):
    """Use literal block style for multiline strings."""
    if '\n' in data:
        data = '\n'.join(line.rstrip() for line in data.split('\n'))
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')  # pyright: ignore[reportUnknownMemberType]
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)  # pyright: ignore[reportUnknownMemberType]


yaml.add_representer(str, str_representer)


def append_to_yaml_atomic(
    file_path: Path, new_data: dict[str, dict[str, str] | str]
) -> None:
    """Atomically append data to a YAML file with file locking."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'a+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            content = f.read()
            data_list: list[dict[str, dict[str, str] | str]] = (
                yaml.safe_load(content) if content else []
            )
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


# Main function
# ====================


async def ask_llm(example_dir: Path, model_name: str) -> None:
    """Ask a single LLM model to answer questions for an example."""
    print(f'Asking {model_name} for {example_dir.name}')

    model_py_path = example_dir / 'model.py'
    if not model_py_path.exists():
        raise ValueError(f'model.py not found in {example_dir}')

    questions_path = example_dir / 'questions.yaml'
    if not questions_path.exists():
        raise ValueError(f'questions.yaml not found in {example_dir}')

    # Load questions
    questions_yaml = yaml.safe_load(questions_path.read_text())
    questions_dict = questions_yaml['questions']
    questions_str = '\n'.join(f'Q{i}: {questions_dict[f"q{i}"]}' for i in range(1, 4))

    # Build context
    context_str = (
        f'Model name: {questions_yaml["model"]}\n'
        f'Core function: {questions_yaml["core_function"]}\n'
        f'Description: {questions_yaml["description"]}\n'
    )

    # Load model definition
    model_definition = model_py_path.read_text()

    # Build prompt
    prompt = f"""
You are an expert code analyst. Your task is to analyze the following model definition and answer the questions:

Context:
{context_str}

Questions:
{questions_str}

Model definition:
{model_definition}
"""

    # Ask the LLM
    agent = Agent[None, Answers](mk_model(model_name), output_type=Answers)
    response = await agent.run(prompt)
    response_dict: dict[str, str] = response.output.model_dump()

    # Build answer structure
    answers: dict[str, dict[str, str] | str] = {
        'model': model_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'q1': {
            'answer': response_dict['q1_answer'],
            'reasoning': response_dict['q1_reasoning'],
        },
        'q2': {
            'answer': response_dict['q2_answer'],
            'reasoning': response_dict['q2_reasoning'],
        },
        'q3': {
            'answer': response_dict['q3_answer'],
            'reasoning': response_dict['q3_reasoning'],
        },
    }

    # Append to YAML
    answer_path = example_dir / 'answer_LLM.yaml'
    append_to_yaml_atomic(answer_path, answers)
    print(f'Done: {model_name} for {example_dir.name}')


# CLI helpers
# ====================


async def process_example(example_dir: Path, models: list[str]) -> None:
    """Process a single example with all specified models."""
    await asyncio.gather(*[ask_llm(example_dir, model) for model in models])


def get_all_examples() -> list[Path]:
    """Get all example directories that have required files."""
    examples: list[Path] = []
    for d in sorted(examples_dir.iterdir()):
        if d.is_dir() and (d / 'model.py').exists() and (d / 'questions.yaml').exists():
            examples.append(d)
    return examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate LLM answers for examples',
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
        help='Skip examples that already have answer_LLM.yaml',
    )
    parser.add_argument(
        '--models',
        nargs='+',
        default=DEFAULT_MODELS,
        help=f'Models to use (default: {DEFAULT_MODELS})',
    )
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Stop on first error instead of continuing',
    )
    return parser.parse_args()


async def main() -> None:
    args: argparse.Namespace = parse_args()

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

    # Filter existing if requested
    if args.skip_existing:
        original_count = len(example_dirs)
        example_dirs = [d for d in example_dirs if not (d / 'answer_LLM.yaml').exists()]
        skipped = original_count - len(example_dirs)
        if skipped:
            print(f'Skipping {skipped} examples with existing answer_LLM.yaml')

    if not example_dirs:
        print('No examples to process')
        return

    models = args.models
    print(f'Processing {len(example_dirs)} examples with {len(models)} models')

    # Process examples
    async def safe_process(example_dir: Path) -> None:
        try:
            await process_example(example_dir, models)
        except Exception as e:
            print(f'Error processing {example_dir.name}: {e}')
            if args.fail_fast:
                raise

    if args.fail_fast:
        for example_dir in example_dirs:
            await process_example(example_dir, models)
    else:
        await asyncio.gather(*[safe_process(d) for d in example_dirs])

    print('Done')


if __name__ == '__main__':
    asyncio.run(main())
