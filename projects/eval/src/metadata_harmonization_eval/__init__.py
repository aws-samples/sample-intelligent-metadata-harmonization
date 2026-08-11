# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Metadata Harmonization Evaluation Package

A standalone testing and benchmarking system for assessing the performance
and accuracy of the metadata harmonization pipeline.
"""

__version__ = "0.1.0"

# Import configuration management
from .config import (
    load_config,
    ConfigurationError,
    load_yaml_file,
    validate_required_fields,
    apply_defaults,
    get_default_config_values,
    create_example_config,
)

# Import dataset loader
from .dataset_loader import DatasetLoader, DatasetLoadError, GroundTruthLoadError

# Import metrics engine
from .metrics_engine import MetricsEngine, MetricsCalculationError

# Import report generator
from .report_generator import ReportGenerator, ReportGenerationError

# Import orchestrator
from .orchestrator import (
    EvaluationOrchestrator,
    EvaluationError,
    ProcessorInitializationError,
    DatasetProcessingError,
)

# Import CLI
from .cli import evaluate

# Import logging configuration
from .logging_config import LoggingConfig

# Import models for easy access
from .models import (
    # Ground Truth Models
    GroundTruthEntry,
    GroundTruth,
    DatasetPair,
    # Metrics Models
    FieldMetrics,
    ErrorTypeMetrics,
    AccuracyMetrics,
    PerformanceMetrics,
    ConfidenceMetrics,
    FalsePositive,
    FalseNegative,
    ErrorAnalysis,
    # Results and Configuration Models
    EvaluationResult,
    BatchEvaluationResult,
    EvaluationConfig,
)

__all__ = [
    "__version__",
    # Configuration Management
    "load_config",
    "ConfigurationError",
    "load_yaml_file",
    "validate_required_fields",
    "apply_defaults",
    "get_default_config_values",
    "create_example_config",
    # Dataset Loader
    "DatasetLoader",
    "DatasetLoadError",
    "GroundTruthLoadError",
    # Metrics Engine
    "MetricsEngine",
    "MetricsCalculationError",
    # Report Generator
    "ReportGenerator",
    "ReportGenerationError",
    # Orchestrator
    "EvaluationOrchestrator",
    "EvaluationError",
    "ProcessorInitializationError",
    "DatasetProcessingError",
    # CLI
    "evaluate",
    # Logging Configuration
    "LoggingConfig",
    # Ground Truth Models
    "GroundTruthEntry",
    "GroundTruth",
    "DatasetPair",
    # Metrics Models
    "FieldMetrics",
    "ErrorTypeMetrics",
    "AccuracyMetrics",
    "PerformanceMetrics",
    "ConfidenceMetrics",
    "FalsePositive",
    "FalseNegative",
    "ErrorAnalysis",
    # Results and Configuration Models
    "EvaluationResult",
    "BatchEvaluationResult",
    "EvaluationConfig",
]
