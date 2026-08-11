# Metadata Harmonization Evaluation Package

**Purpose**: Standalone evaluation and benchmarking system for measuring accuracy, performance, and reliability of the metadata harmonization pipeline.

**Version**: 0.1.0

## Overview

The evaluation package processes synthetic test datasets with known ground truth through the harmonization workflow and generates detailed performance metrics.

Key capabilities:
- Accuracy assessment: precision, recall, F1 scores
- Performance benchmarking: processing time, throughput, memory
- Cost estimation: AWS Bedrock API costs
- Confidence analysis: score distributions and correlations
- Error pattern detection: common failure modes

## Quick Start

```bash
cd projects/eval

# Install
pip install -e .

# Run single dataset
mh-eval data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40.csv

# Run with markdown report
mh-eval --format markdown data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40.csv

# Run batch evaluation
mh-eval --batch data/synthetic_dataset/
```

### Using Makefile (Recommended)

The Makefile automatically loads config:

```bash
# From project root
make runEval PATH_OR_FILTER=data/synthetic_dataset/simple_test.csv

# Run on specific dataset
make runEval PATH_OR_FILTER=data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40.csv

# Run on all datasets in directory
make runEval PATH_OR_FILTER=data/synthetic_dataset

# Filter by error rate
make runEval PATH_OR_FILTER=err40

# Add arguments
make runEval PATH_OR_FILTER=data/synthetic_dataset/simple_test.csv ARGS="--verbose"
```

## Configuration

### YAML Configuration

```yaml
# config.yaml
processor_config_path: "config.yaml"
data_directory: "data/synthetic_dataset"
schema_program_id: "cyclospora_program"
schema_core_id: "cyclospora_core"

output_directory: "evaluation_results"
report_formats: ["json", "markdown"]
verbose_logging: false
```

### Cost Configuration

```yaml
bedrock_pricing:
  llm_models:
    "amazon.nova-pro-v1:0":
      input_price_per_1k: 0.0008
      output_price_per_1k: 0.0032
    "anthropic.claude-3-sonnet-20240229-v1:0":
      input_price_per_1k: 0.003
      output_price_per_1k: 0.015

  embedding_models:
    "amazon.titan-embed-text-v2:0": 0.00002
    "cohere.embed-english-v3": 0.0001
```

## CLI Options

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Path to evaluation configuration YAML file |
| `-o, --output-dir PATH` | Output directory for results (default: evaluation_results) |
| `-f, --format [json\|markdown\|both]` | Report format (default: both) |
| `-v, --verbose` | Enable verbose logging |
| `-b, --batch` | Run batch evaluation mode |
| `-a, --auto-discover PATH` | Auto-discover datasets in directory |
| `--error-rate-filter TEXT` | Filter by error rate pattern (e.g., 'err40') |
| `--dataset-pattern TEXT` | Filter by dataset name pattern |
| `--program-id TEXT` | Override schema program ID |
| `--core-id TEXT` | Override schema core ID |

## Dataset Naming Convention

Datasets follow: `synthetic_cyclospora_dataset_{id}_err{rate}.csv`

Example: `synthetic_cyclospora_dataset_1_err40.csv` (40% error rate)

### Ground Truth Format

Ground truth JSON files contain known correct values:

```json
[
  {
    "row": 1,
    "field": "submitter_name",
    "schema_field": "SubmitterName",
    "original": "CDC Parasite Domestic Surveillance Team",
    "error": "CDt Parasite Domestic Surveillance Team",
    "error_type": "abbreviation",
    "valid_options": ["CDC Parasite Domestic Surveillance Team"]
  }
]
```

## Output Structure

Results saved to timestamped directories:

```
evaluation_results/
└── eval-20241028-103000/
    ├── synthetic_cyclospora_dataset_1_err40_results.json
    ├── synthetic_cyclospora_dataset_1_err40_summary.md
    └── batch_comparison.md  (batch mode only)
```

## Project Structure

```
projects/eval/
├── pyproject.toml
├── README.md
├── config.yaml.example
├── src/
│   └── metadata_harmonization_eval/
│       ├── __init__.py
│       ├── cli.py
│       ├── orchestrator.py
│       ├── dataset_loader.py
│       ├── metrics_engine.py
│       ├── report_generator.py
│       ├── config.py
│       └── models.py
├── tests/
│   ├── test_dataset_loader.py
│   ├── test_metrics_engine.py
│   ├── test_report_generator.py
│   ├── test_orchestrator.py
│   └── test_e2e_evaluation.py
└── evaluation_results/
```

## Development

### Setup

```bash
cd projects/eval

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=metadata_harmonization_eval

# Generate coverage report
pytest --cov=metadata_harmonization_eval --cov-report=html
```

### Key Dependencies

- pandas>=2.0.0: DataFrame operations
- click>=8.0.0: CLI interface
- pydantic>=2.0.0: Data modeling
- loguru>=0.7.0: Structured logging
- pyyaml>=6.0.0: Configuration parsing

## Integration with Processor

```python
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings

config = load_processor_settings("config.yaml")
processor = MetadataHarmonizationProcessor(
    config=config,
    session_id=f"eval-{timestamp}",
    session_config={"storage_dir": eval_session_dir}
)

results = await processor.process(
    metadata_df=dataset_df,
    program_id=program_id,
    core_id=core_id,
    job_id=f"eval-job-{timestamp}"
)
```

## Programmatic Usage

```python
from pathlib import Path
from metadata_harmonization_eval import (
    EvaluationOrchestrator,
    EvaluationConfig,
    DatasetLoader
)

# Load configuration
config = EvaluationConfig.from_yaml(Path("config.yaml"))

# Create orchestrator
orchestrator = EvaluationOrchestrator(config)

# Load dataset pair
loader = DatasetLoader()
dataset_pair = loader.discover_datasets(Path("data/synthetic_dataset"))[0]

# Run evaluation
result = await orchestrator.evaluate_dataset(dataset_pair)

# Access results
print(f"F1 Score: {result.accuracy_metrics.f1_score:.3f}")
print(f"Processing Time: {result.performance_metrics.total_duration_seconds:.2f}s")
```
