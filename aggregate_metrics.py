# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "polars",
#     "pyyaml",
#     "matplotlib",
#     "seaborn",
#     "numpy",
# ]
# ///
# pyright: basic
"""
Aggregate metrics from all examples and create visualizations.

- deps: examples/*/metrics.yaml
- target: analysis/*.csv, analysis/*.png
"""

from math import log2
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
import yaml

script_dir = Path(__file__).parent
examples_dir = script_dir / 'examples'
output_dir = script_dir / 'analysis'

METRIC_ORDER = [
    'state_space_estimation_accuracy',
    'control_flow_understanding',
    'edge_case_detection',
    'decision_boundary_clarity',
    'outcome_precision',
    'direction_accuracy',
    'coverage_completeness',
]

METRIC_LABELS = {
    'state_space_estimation_accuracy': 'State Space\nEstimation',
    'control_flow_understanding': 'Control Flow\nUnderstanding',
    'edge_case_detection': 'Edge Case\nDetection',
    'decision_boundary_clarity': 'Decision\nBoundary',
    'outcome_precision': 'Outcome\nPrecision',
    'direction_accuracy': 'Direction\nAccuracy',
    'coverage_completeness': 'Coverage\nCompleteness',
}

COLORS = ['#E63946', '#457B9D', '#F77F00', '#06A77D', '#9D4EDD', '#E9C46A', '#264653']

# q1, q2 use decomp; q3 uses vg
QUESTION_METHOD: dict[str, str] = {
    'q1': 'decomp',
    'q2': 'decomp',
    'q3': 'vg',
}

# Which methods each metric applies to
METRIC_APPLICABLE_METHODS: dict[str, list[str]] = {
    'state_space_estimation_accuracy': ['decomp'],
    'control_flow_understanding': ['vg', 'decomp'],
    'edge_case_detection': ['vg', 'decomp'],
    'decision_boundary_clarity': ['vg', 'decomp'],
    'outcome_precision': ['vg', 'decomp'],
    'direction_accuracy': ['vg'],
    'coverage_completeness': ['vg', 'decomp'],
}


def get_label(metric: str, multiline: bool = True) -> str:
    """Get display label for a metric."""
    label = METRIC_LABELS.get(metric, metric)
    if not multiline:
        label = label.replace('\n', ' ')
    return label


def sort_by_metric_order(df: pl.DataFrame) -> pl.DataFrame:
    """Sort dataframe by canonical metric order."""
    return (
        df.with_columns(
            pl.col('metric')
            .map_elements(
                lambda x: METRIC_ORDER.index(x) if x in METRIC_ORDER else 999,
                return_dtype=pl.Int64,
            )
            .alias('_order')
        )
        .sort('_order')
        .drop('_order')
    )


def find_metrics_files() -> list[Path]:
    """Find all metrics.yaml files in examples/."""
    return sorted(examples_dir.glob('*/metrics.yaml'))


def load_metrics(file_path: Path) -> list[dict[str, Any]]:
    """Load metrics from a YAML file."""
    with open(file_path) as f:
        return yaml.safe_load(f)


def normalize_state_space_score(n_llm: int | str, n_decomp: int) -> float:
    """Normalize state_space_estimation_accuracy score to [0, 1]."""
    if n_llm == 'unknown':
        return 0.0
    n_llm = cast(int, n_llm)
    diff = abs(n_llm - n_decomp)
    if diff == 0:
        return 1.0
    return 1.0 / (1.0 + log2(diff + 1))


def aggregate_metrics() -> pl.DataFrame:
    """Aggregate all metrics from examples/."""
    files = find_metrics_files()
    print(f'Found {len(files)} metrics.yaml files')

    rows = []
    for file_path in files:
        project_name = file_path.parent.name
        data = load_metrics(file_path)

        if not data:
            print(f'Warning: No data in {file_path}')
            continue

        for eval_entry in data:
            answer_model = eval_entry.get('answer_model', 'unknown')
            eval_model = eval_entry.get('eval_model', 'unknown')
            metrics = eval_entry.get('metrics', {})

            for question_id, question_metrics in metrics.items():
                if not question_metrics:
                    continue

                for metric_name, metric_value in question_metrics.items():
                    if metric_name == 'overall_summary' or metric_value is None:
                        continue

                    # Skip metrics not applicable to this question's method
                    question_method = QUESTION_METHOD[question_id]
                    applicable = METRIC_APPLICABLE_METHODS[metric_name]
                    if question_method and applicable and question_method not in applicable:
                        continue

                    if metric_name == 'state_space_estimation_accuracy':
                        n_llm = metric_value.get('n_llm_estimated_scenarios', 'unknown')
                        n_decomp = metric_value.get(
                            'n_decomposition_exact_scenarios', 0
                        )
                        score_float = normalize_state_space_score(n_llm, n_decomp)
                    else:
                        score = metric_value.get('score')
                        try:
                            score_float = float(score)
                        except (ValueError, TypeError):
                            print(
                                f'Warning: Invalid score {score} for {metric_name} in {project_name}/{question_id}'
                            )
                            continue

                    rows.append(
                        {
                            'answer_model': answer_model,
                            'eval_model': eval_model,
                            'project': project_name,
                            'question': question_id,
                            'metric': metric_name,
                            'score': score_float,
                        }
                    )

    return pl.DataFrame(rows)


def create_radar_chart(df_agg: pl.DataFrame) -> None:
    """Create a radar chart comparing models across metrics."""
    model_metrics = (
        df_agg.group_by(['model', 'metric'])
        .agg(pl.col('score').mean())
        .sort(['model', 'metric'])
    )

    models = sorted(model_metrics['model'].unique().to_list())
    available_metrics = [
        m for m in METRIC_ORDER if m in model_metrics['metric'].unique().to_list()
    ]
    labels = [get_label(m) for m in available_metrics]
    num_vars = len(available_metrics)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))

    for idx, model in enumerate(models):
        values = []
        for metric in available_metrics:
            score = model_metrics.filter(
                (pl.col('model') == model) & (pl.col('metric') == metric)
            )['score']
            values.append(score[0] if len(score) > 0 else 0.0)
        values += values[:1]

        color = COLORS[idx % len(COLORS)]
        ax.plot(angles, values, 'o-', linewidth=2.5, label=model, color=color)
        ax.fill(angles, values, alpha=0.15, color=color)

    # Reference line at 1.0
    ax.plot(
        angles,
        [1.0] * (num_vars + 1),
        '--',
        linewidth=2,
        label='LLM + CodeLogician',
        color='#2A9D8F',
        alpha=0.6,
    )

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(True)
    plt.title('Model Comparison Across Metrics', size=16, weight='bold', pad=30)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    plt.tight_layout()
    plt.savefig(output_dir / 'model_comparison_radar.png', dpi=300, bbox_inches='tight')
    print(f'Saved: {output_dir}/model_comparison_radar.png')
    plt.close()


def create_bar_chart(df_agg: pl.DataFrame) -> None:
    """Create a grouped bar chart comparing models across metrics."""
    model_metrics = (
        df_agg.group_by(['model', 'metric'])
        .agg(pl.col('score').mean())
        .sort(['model', 'metric'])
    )

    models = sorted(model_metrics['model'].unique().to_list())
    available_metrics = [
        m for m in METRIC_ORDER if m in model_metrics['metric'].unique().to_list()
    ]
    labels = [get_label(m) for m in available_metrics]

    fig, ax = plt.subplots(figsize=(16, 10))
    x = np.arange(len(labels))
    width = 0.8 / len(models)

    for idx, model in enumerate(models):
        values = []
        for metric in available_metrics:
            score = model_metrics.filter(
                (pl.col('model') == model) & (pl.col('metric') == metric)
            )['score']
            values.append(score[0] if len(score) > 0 else 0.0)

        offset = (idx - len(models) / 2 + 0.5) * width
        bars = ax.bar(
            x + offset,
            values,
            width,
            label=model,
            color=COLORS[idx % len(COLORS)],
            alpha=0.8,
            edgecolor='black',
        )

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.01,
                f'{height:.2f}',
                ha='center',
                va='bottom',
                fontsize=9,
                weight='bold',
            )

    ax.axhline(y=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    ax.set_xlabel('Metrics', size=15, weight='bold')
    ax.set_ylabel('Score (0-1)', size=15, weight='bold')
    ax.set_title('Model Comparison Across All Metrics', size=17, weight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha='center')
    ax.set_ylim(0, 1.15)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'model_comparison_bars.png', dpi=300, bbox_inches='tight')
    print(f'Saved: {output_dir}/model_comparison_bars.png')
    plt.close()


def create_overall_performance_chart(df_agg: pl.DataFrame) -> None:
    """Create a horizontal bar chart showing overall average score for each model."""
    model_averages = (
        df_agg.group_by('model')
        .agg(pl.col('score').mean().alias('avg_score'))
        .sort('avg_score')
    )

    fig, ax = plt.subplots(figsize=(12, 8))
    models = model_averages['model'].to_list()
    scores = model_averages['avg_score'].to_list()
    bar_colors = [COLORS[i % len(COLORS)] for i in range(len(models))]

    bars = ax.barh(models, scores, color=bar_colors, alpha=0.8, edgecolor='black')

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2.0,
            f'{score:.3f}',
            ha='left',
            va='center',
            fontsize=13,
            weight='bold',
        )

    ax.axvline(x=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    ax.set_xlabel('Overall Average Score', size=14, weight='bold')
    ax.set_ylabel('Model', size=14, weight='bold')
    ax.set_title('Overall Performance: Models', size=16, weight='bold', pad=20)
    ax.set_xlim(0, 1.15)
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        output_dir / 'overall_performance_models.png', dpi=300, bbox_inches='tight'
    )
    print(f'Saved: {output_dir}/overall_performance_models.png')
    plt.close()


def create_summary_plots(df_agg: pl.DataFrame) -> None:
    """Create summary plots."""
    sns.set_style('whitegrid')
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Average score by metric (ordered)
    ax1 = axes[0, 0]
    metric_avg = df_agg.group_by('metric').agg(pl.col('score').mean())
    metric_avg = sort_by_metric_order(metric_avg)
    labels = [get_label(m, multiline=False) for m in metric_avg['metric'].to_list()]
    ax1.barh(
        labels,
        metric_avg['score'].to_list(),
        color='#5B9BD5',
        alpha=0.8,
        edgecolor='black',
    )
    ax1.set_xlabel('Average Score', weight='bold')
    ax1.set_title('Average Score by Metric', weight='bold')
    ax1.set_xlim([0, 1.15])
    ax1.axvline(x=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    ax1.grid(axis='x', alpha=0.3)

    # 2. Box plot by metric
    ax2 = axes[0, 1]
    ordered_metrics = [
        m for m in METRIC_ORDER if m in df_agg['metric'].unique().to_list()
    ]
    metric_scores = [
        df_agg.filter(pl.col('metric') == m)['score'].to_list() for m in ordered_metrics
    ]
    labels = [get_label(m) for m in ordered_metrics]
    ax2.boxplot(
        metric_scores,
        tick_labels=labels,
        patch_artist=True,
        boxprops=dict(facecolor='#5B9BD5', alpha=0.7),
        medianprops=dict(color='#E63946', linewidth=2),
    )
    ax2.set_ylabel('Score', weight='bold')
    ax2.set_title('Score Distribution by Metric', weight='bold')
    ax2.set_ylim([-0.1, 1.1])
    ax2.axhline(y=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    plt.sca(ax2)
    plt.xticks(rotation=45, ha='right')

    # 3. Median score by metric (ordered)
    ax3 = axes[1, 0]
    metric_median = df_agg.group_by('metric').agg(pl.col('score').median())
    metric_median = sort_by_metric_order(metric_median)
    labels = [get_label(m, multiline=False) for m in metric_median['metric'].to_list()]
    ax3.barh(
        labels,
        metric_median['score'].to_list(),
        color='#5B9BD5',
        alpha=0.8,
        edgecolor='black',
    )
    ax3.set_xlabel('Median Score', weight='bold')
    ax3.set_title('Median Score by Metric', weight='bold')
    ax3.set_xlim([0, 1.15])
    ax3.axvline(x=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    ax3.grid(axis='x', alpha=0.3)

    # 4. Average score by model
    ax4 = axes[1, 1]
    model_avg = df_agg.group_by('model').agg(pl.col('score').mean()).sort('score')
    colors_model = [COLORS[i % len(COLORS)] for i in range(len(model_avg))]
    ax4.barh(
        model_avg['model'].to_list(),
        model_avg['score'].to_list(),
        color=colors_model,
        alpha=0.8,
        edgecolor='black',
    )
    ax4.set_xlabel('Average Score', weight='bold')
    ax4.set_title('Average Score by Model', weight='bold')
    ax4.set_xlim([0, 1.15])
    ax4.axvline(x=1.0, color='#2A9D8F', linestyle='--', linewidth=2, alpha=0.7)
    ax4.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'metrics_summary.png', dpi=300, bbox_inches='tight')
    print(f'Saved: {output_dir}/metrics_summary.png')
    plt.close()


def save_csv_files(df: pl.DataFrame) -> None:
    """Save aggregated data to CSV files."""
    df.write_csv(output_dir / 'aggregated_metrics_full.csv')

    # Aggregate across eval_models first
    df_agg = (
        df.group_by(['answer_model', 'project', 'question', 'metric'])
        .agg(pl.col('score').mean())
        .rename({'answer_model': 'model'})
    )

    # Average over project and question
    agg_metrics = df_agg.group_by(['model', 'metric']).agg(pl.col('score').mean())
    agg_metrics.write_csv(output_dir / 'aggregated_metrics.csv')

    # Model-metric pivot table (sorted for consistent ordering)
    model_metric_avg = (
        df_agg.group_by(['model', 'metric'])
        .agg(pl.col('score').mean().alias('average_score'))
        .sort(['model', 'metric'])
    )
    pivot = model_metric_avg.pivot(values='average_score', index='metric', on='model')
    pivot.write_csv(output_dir / 'model_metric_pivot.csv')

    print(f'Saved CSV files to {output_dir}/')


def print_summary(df: pl.DataFrame) -> None:
    """Print summary statistics."""
    df_agg = df.group_by(['answer_model', 'project', 'question', 'metric']).agg(
        pl.col('score').mean()
    )

    print('\n' + '=' * 60)
    print('SUMMARY STATISTICS')
    print('=' * 60)
    print(f'Total samples: {len(df_agg)}')
    print(f'Models: {df["answer_model"].n_unique()}')
    print(f'Projects: {df["project"].n_unique()}')
    print(f'Metrics: {df["metric"].n_unique()}')

    stats = df_agg.select(
        [
            pl.col('score').mean().alias('mean'),
            pl.col('score').median().alias('median'),
            pl.col('score').std().alias('std'),
        ]
    ).row(0, named=True)
    print(
        f'\nOverall: mean={stats["mean"]:.3f}, median={stats["median"]:.3f}, std={stats["std"]:.3f}'
    )
    print('=' * 60)


def create_sample_count_table(df_agg: pl.DataFrame) -> None:
    """Create a table image showing sample counts per model and metric."""
    # Derive method from question using QUESTION_METHOD
    df_with_method = df_agg.with_columns(
        pl.col('question')
        .map_elements(lambda q: QUESTION_METHOD.get(q, 'unknown'), return_dtype=pl.Utf8)
        .alias('method')
    )

    # Count distinct (project, question) per method per model
    method_counts = (
        df_with_method.group_by(['model', 'method'])
        .agg(pl.struct('project', 'question').n_unique().alias('n'))
        .sort(['model', 'method'])
    )
    method_pivot = method_counts.pivot(
        values='n', index='method', on='model'
    ).fill_null(0)

    # Per-metric sample counts
    metric_counts = (
        df_agg.group_by(['model', 'metric'])
        .agg(pl.col('score').count().alias('n'))
        .sort(['model', 'metric'])
    )
    metric_pivot = metric_counts.pivot(
        values='n', index='metric', on='model'
    ).fill_null(0)

    # Sort metric rows by METRIC_ORDER
    ordered_metrics = [m for m in METRIC_ORDER if m in metric_pivot['metric'].to_list()]
    metric_pivot = metric_pivot.filter(pl.col('metric').is_in(ordered_metrics))
    metric_pivot = sort_by_metric_order(metric_pivot)

    col_labels = sorted([c for c in metric_pivot.columns if c != 'metric'])

    # Build rows: method counts first, then metric counts
    row_labels: list[str] = []
    cell_data: list[list[str]] = []

    # Method answer counts
    method_order = ['vg', 'decomp']
    method_display = {'vg': '# Answers (vg)', 'decomp': '# Answers (decomp)'}
    for method in method_order:
        if method in method_pivot['method'].to_list():
            row_labels.append(method_display[method])
            cell_data.append(
                [
                    str(method_pivot.filter(pl.col('method') == method)[c][0])
                    for c in col_labels
                ]
            )

    n_method_rows = len(row_labels)

    # Metric sample counts
    for m in metric_pivot['metric'].to_list():
        row_labels.append(get_label(m, multiline=False))
        cell_data.append(
            [str(metric_pivot.filter(pl.col('metric') == m)[c][0]) for c in col_labels]
        )

    fig, ax = plt.subplots(
        figsize=(
            max(8, 2 + 2.5 * len(col_labels)),
            1.5 + 0.5 * len(row_labels),
        )
    )
    ax.axis('off')
    table = ax.table(
        cellText=cell_data,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc='center',
        loc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)

    # Style header row
    for j in range(len(col_labels)):
        table[0, j].set_facecolor('#457B9D')
        table[0, j].set_text_props(color='white', weight='bold')
    # Style row labels
    for i in range(len(row_labels)):
        table[i + 1, -1].set_text_props(weight='bold')
        if i < n_method_rows:
            table[i + 1, -1].set_facecolor('#D4E6F1')
            for j in range(len(col_labels)):
                table[i + 1, j].set_facecolor('#D4E6F1')
        else:
            table[i + 1, -1].set_facecolor('#E8E8E8')

    ax.set_title('Sample Count per Model and Metric', size=14, weight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / 'sample_count_table.png', dpi=300, bbox_inches='tight')
    print(f'Saved: {output_dir}/sample_count_table.png')
    plt.close()


def main() -> None:
    output_dir.mkdir(exist_ok=True)
    print('Aggregating metrics from examples/...')

    df = aggregate_metrics()
    if len(df) == 0:
        print('No data to analyze!')
        return

    print_summary(df)
    save_csv_files(df)

    # Aggregate across eval_models for plotting
    df_agg = (
        df.group_by(['answer_model', 'project', 'question', 'metric'])
        .agg(pl.col('score').mean())
        .rename({'answer_model': 'model'})
    )

    print('\nGenerating plots...')
    create_summary_plots(df_agg)
    create_radar_chart(df_agg)
    create_bar_chart(df_agg)
    create_overall_performance_chart(df_agg)
    create_sample_count_table(df_agg)

    print('\nDone!')


if __name__ == '__main__':
    main()
