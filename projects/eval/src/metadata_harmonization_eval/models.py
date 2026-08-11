# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Data models for the evaluation package.

This module contains all Pydantic models used throughout the evaluation system,
including ground truth data, metrics, results, and configuration.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================================
# Ground Truth Models (Subtask 2.1)
# ============================================================================


class GroundTruthEntry(BaseModel):
    """
    Represents a single error entry in the ground truth data.

    Attributes:
        row: Row number in the dataset (0-indexed)
        field: Original field name in the CSV
        schema_field: Corresponding field name in the target schema
        original: The correct value
        error: The erroneous value present in the dataset
        error_type: Type of error (e.g., 'abbreviation', 'fuzzy', 'case_spacing')
        valid_options: List of valid values for this field
    """

    row: int = Field(..., ge=0, description="Row number in the dataset")
    field: str = Field(..., min_length=1, description="Original field name")
    schema_field: str = Field(..., min_length=1, description="Schema field name")
    original: str = Field(..., description="Correct value")
    error: str = Field(..., description="Erroneous value in dataset")
    error_type: str = Field(..., min_length=1, description="Type of error")
    valid_options: List[str] = Field(..., min_length=1, description="Valid values")

    model_config = ConfigDict(frozen=True)


class GroundTruth(BaseModel):
    """
    Container for all ground truth entries in a dataset.

    Attributes:
        entries: List of all error entries
        error_rate: Percentage of errors in the dataset (0.0 to 1.0)
        total_errors: Total number of errors in the dataset
    """

    entries: List[GroundTruthEntry] = Field(..., description="All error entries")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate (0-1)")
    total_errors: int = Field(..., ge=0, description="Total number of errors")


class DatasetPair(BaseModel):
    """
    Represents a paired CSV dataset and its ground truth JSON file.

    Attributes:
        csv_path: Path to the CSV dataset file
        ground_truth_path: Path to the ground truth JSON file
        dataset_name: Name identifier for the dataset
        error_rate: Error rate extracted from filename or ground truth
    """

    csv_path: Path = Field(..., description="Path to CSV dataset")
    ground_truth_path: Path = Field(..., description="Path to ground truth JSON")
    dataset_name: str = Field(..., min_length=1, description="Dataset identifier")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Dataset error rate")

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============================================================================
# Metrics Models (Subtask 2.2)
# ============================================================================


class FieldMetrics(BaseModel):
    """
    Comprehensive accuracy metrics for a specific field/column.

    This model provides detailed metrics for each column in the dataset,
    including full confusion matrix values, derived metrics, confidence statistics,
    and error type breakdown.

    Attributes:
        field_name: Name of the field/column
        precision: Precision score for this field
        recall: Recall score for this field
        f1_score: F1 score for this field
        accuracy: Accuracy score for this field
        total_errors: Total errors in ground truth for this field
        detected_errors: Number of errors correctly detected
        missed_errors: Number of errors not detected
        true_positives: Count of correctly detected errors (same as detected_errors)
        false_positives: Count of incorrectly flagged errors
        false_negatives: Count of missed errors (same as missed_errors)
        true_negatives: Count of correctly identified non-errors
        total_records_checked: Number of records that had this field
        mean_confidence: Mean confidence score for detections in this field
        median_confidence: Median confidence score for detections in this field
        error_type_counts: Count of each error type in ground truth for this field
        error_type_detection_rates: Detection rate for each error type in this field
    """

    field_name: str = Field(..., min_length=1, description="Name of the field/column")

    # Core metrics (existing)
    precision: float = Field(..., ge=0.0, le=1.0, description="Precision score")
    recall: float = Field(..., ge=0.0, le=1.0, description="Recall score")
    f1_score: float = Field(..., ge=0.0, le=1.0, description="F1 score")

    # Enhanced metrics (new)
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Accuracy score")

    # Volume metrics (existing + enhanced)
    total_errors: int = Field(..., ge=0, description="Total errors in ground truth")
    detected_errors: int = Field(..., ge=0, description="Errors correctly detected")
    missed_errors: int = Field(..., ge=0, description="Errors not detected")

    # Full confusion matrix (new)
    true_positives: int = Field(default=0, ge=0, description="Correctly detected errors")
    false_positives: int = Field(default=0, ge=0, description="Incorrectly flagged errors")
    false_negatives: int = Field(default=0, ge=0, description="Missed errors")
    true_negatives: int = Field(default=0, ge=0, description="Correctly identified non-errors")

    # Record count (new)
    total_records_checked: int = Field(default=0, ge=0, description="Records with this field")

    # Confidence statistics (new)
    mean_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean confidence score")
    median_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Median confidence score")

    # Error type breakdown (new)
    error_type_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count of each error type in ground truth"
    )
    error_type_detection_rates: Dict[str, float] = Field(
        default_factory=dict, description="Detection rate for each error type"
    )


class ErrorTypeMetrics(BaseModel):
    """
    Detection metrics for a specific error type.

    Attributes:
        error_type: Type of error (e.g., 'abbreviation', 'fuzzy')
        detection_rate: Percentage of errors of this type detected
        total_count: Total occurrences of this error type
        detected_count: Number of occurrences detected
    """

    error_type: str = Field(..., min_length=1)
    detection_rate: float = Field(..., ge=0.0, le=1.0)
    total_count: int = Field(..., ge=0)
    detected_count: int = Field(..., ge=0)


class CostMetrics(BaseModel):
    """
    Cost metrics for Bedrock API usage.

    Tracks token usage and estimated costs for both LLM and embedding model
    API calls to AWS Bedrock during evaluation.

    Attributes:
        llm_input_tokens: Number of input tokens sent to LLM
        llm_output_tokens: Number of output tokens generated by LLM
        llm_total_tokens: Total LLM tokens (input + output)
        llm_input_cost: Cost for LLM input tokens in USD
        llm_output_cost: Cost for LLM output tokens in USD
        llm_total_cost: Total LLM cost in USD
        llm_api_calls: Number of LLM API calls made
        embedding_tokens: Number of tokens processed by embedding model
        embedding_cost: Cost for embedding tokens in USD
        embedding_api_calls: Number of embedding API calls made
        total_cost: Total Bedrock cost (LLM + embedding) in USD
        cost_per_error_detected: Cost per error detected (None if no errors detected)
        model_id: Specific model ID used for this node's operations (for per-node metrics)
        llm_model_id: ID of the LLM model used (for aggregate metrics)
        embedding_model_id: ID of the embedding model used (for aggregate metrics)
    """

    # LLM costs
    llm_input_tokens: int = Field(default=0, ge=0, description="LLM input tokens")
    llm_output_tokens: int = Field(default=0, ge=0, description="LLM output tokens")
    llm_total_tokens: int = Field(default=0, ge=0, description="Total LLM tokens")
    llm_input_cost: float = Field(default=0.0, ge=0.0, description="LLM input cost in USD")
    llm_output_cost: float = Field(default=0.0, ge=0.0, description="LLM output cost in USD")
    llm_total_cost: float = Field(default=0.0, ge=0.0, description="Total LLM cost in USD")
    llm_api_calls: int = Field(default=0, ge=0, description="Number of LLM API calls")

    # Embedding costs
    embedding_tokens: int = Field(default=0, ge=0, description="Embedding tokens")
    embedding_cost: float = Field(default=0.0, ge=0.0, description="Embedding cost in USD")
    embedding_api_calls: int = Field(default=0, ge=0, description="Number of embedding API calls")

    # Total costs
    total_cost: float = Field(default=0.0, ge=0.0, description="Total Bedrock cost in USD")
    cost_per_error_detected: Optional[float] = Field(
        None, ge=0.0, description="Cost per error detected (None if no errors detected)"
    )

    # Model information
    llm_model_id: Optional[str] = Field(None, description="LLM model ID")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID")


class NodeMetrics(BaseModel):
    """
    Correction metrics for a specific correction node.

    Tracks the performance of individual correction nodes (fuzzy_matching,
    contextual_inference, semantic_prediction, llm_resolution) in the
    enum correction pipeline.

    Attributes:
        node_name: Name of the correction node
        total_corrections: Total number of corrections made by this node
        successful_corrections: Number of corrections that matched ground truth
        success_rate: Percentage of successful corrections
        mean_confidence: Average confidence score for this node's corrections
        median_confidence: Median confidence score
        high_confidence_count: Number of corrections with confidence > 0.8
        high_confidence_percentage: Percentage of high-confidence corrections
        error_type_breakdown: Count of corrections by error type
        cost_metrics: Bedrock cost metrics for this node
        cost_per_correction: Cost per successful correction
    """

    node_name: str = Field(..., min_length=1, description="Name of the correction node")
    total_corrections: int = Field(default=0, ge=0, description="Total corrections made")
    successful_corrections: int = Field(default=0, ge=0, description="Successful corrections")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")
    mean_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean confidence")
    median_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Median confidence")
    high_confidence_count: int = Field(default=0, ge=0, description="High confidence (>0.8) count")
    high_confidence_percentage: float = Field(default=0.0, ge=0.0, le=1.0, description="% high confidence")
    error_type_breakdown: Dict[str, int] = Field(default_factory=dict, description="Count of corrections by error type")

    # Cost metrics
    cost_metrics: Optional[CostMetrics] = Field(None, description="Bedrock cost metrics for this node")
    cost_per_correction: Optional[float] = Field(None, ge=0.0, description="Cost per successful correction")


class AccuracyMetrics(BaseModel):
    """
    Overall accuracy metrics for the evaluation.

    Attributes:
        precision: Overall precision score
        recall: Overall recall score
        f1_score: Overall F1 score
        true_positives: Count of true positive predictions
        false_positives: Count of false positive predictions
        false_negatives: Count of false negative predictions
        true_negatives: Count of true negative predictions
        accuracy: Overall accuracy score
        field_metrics: Per-field accuracy breakdown
        error_type_metrics: Per-error-type detection breakdown
    """

    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    true_positives: int = Field(..., ge=0)
    false_positives: int = Field(..., ge=0)
    false_negatives: int = Field(..., ge=0)
    true_negatives: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0.0, le=1.0)

    # Per-field and per-error-type breakdowns
    field_metrics: Dict[str, FieldMetrics] = Field(default_factory=dict)
    error_type_metrics: Dict[str, ErrorTypeMetrics] = Field(default_factory=dict)


class PerformanceMetrics(BaseModel):
    """
    Performance and timing metrics for the evaluation.

    Attributes:
        total_duration_seconds: Total processing time in seconds
        per_record_duration_ms: Average time per record in milliseconds
        records_per_second: Processing throughput
        schema_alignment_duration: Time spent in schema alignment stage
        validation_duration: Time spent in validation stage
        prediction_duration: Time spent in prediction stage
        peak_memory_mb: Peak memory usage in megabytes
    """

    total_duration_seconds: float = Field(..., ge=0.0)
    per_record_duration_ms: float = Field(..., ge=0.0)
    records_per_second: float = Field(..., ge=0.0)

    # Stage timings
    schema_alignment_duration: float = Field(..., ge=0.0)
    validation_duration: float = Field(..., ge=0.0)
    prediction_duration: float = Field(..., ge=0.0)

    # Resource usage
    peak_memory_mb: float = Field(..., ge=0.0)


class ConfidenceMetrics(BaseModel):
    """
    Confidence score distribution and analysis.

    Attributes:
        mean_confidence: Mean confidence score across all predictions
        median_confidence: Median confidence score
        std_deviation: Standard deviation of confidence scores
        min_confidence: Minimum confidence score
        max_confidence: Maximum confidence score
        confidence_distribution: Histogram of confidence scores by bucket
        high_confidence_accuracy: Accuracy for predictions with confidence > 0.8
        low_confidence_accuracy: Accuracy for predictions with confidence < 0.5
    """

    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    median_confidence: float = Field(..., ge=0.0, le=1.0)
    std_deviation: float = Field(..., ge=0.0)
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    max_confidence: float = Field(..., ge=0.0, le=1.0)

    # Distribution buckets (e.g., "0.0-0.2": 5, "0.2-0.4": 10)
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)

    # Confidence vs accuracy correlation
    high_confidence_accuracy: float = Field(..., ge=0.0, le=1.0)
    low_confidence_accuracy: float = Field(..., ge=0.0, le=1.0)


class FalsePositive(BaseModel):
    """
    Details of a false positive prediction.

    Attributes:
        row: Row number where false positive occurred
        field: Field name
        predicted_error: What the system incorrectly predicted as an error
        actual_value: The actual (correct) value
        confidence: Confidence score of the incorrect prediction (None if no correction attempted)
    """

    row: int = Field(..., ge=0)
    field: str = Field(..., min_length=1)
    predicted_error: str
    actual_value: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class FalseNegative(BaseModel):
    """
    Details of a false negative (missed error).

    Attributes:
        row: Row number where error was missed
        field: Field name
        expected_correction: What should have been detected/corrected
        actual_error: The error value that was not detected
        error_type: Type of error that was missed
    """

    row: int = Field(..., ge=0)
    field: str = Field(..., min_length=1)
    expected_correction: str
    actual_error: str
    error_type: str = Field(..., min_length=1)


class ErrorAnalysis(BaseModel):
    """
    Detailed error pattern analysis.

    Attributes:
        total_errors: Total errors in ground truth
        detected_errors: Number of errors correctly detected
        missed_errors: Number of errors not detected
        false_alarms: Number of false positive predictions
        most_common_error_types: List of (error_type, count) tuples
        most_problematic_fields: List of (field_name, missed_count) tuples
        false_positives: Detailed list of false positive predictions
        false_negatives: Detailed list of missed errors
    """

    total_errors: int = Field(..., ge=0)
    detected_errors: int = Field(..., ge=0)
    missed_errors: int = Field(..., ge=0)
    false_alarms: int = Field(..., ge=0)

    # Error patterns
    most_common_error_types: List[Tuple[str, int]] = Field(default_factory=list)
    most_problematic_fields: List[Tuple[str, int]] = Field(default_factory=list)

    # Detailed breakdowns
    false_positives: List[FalsePositive] = Field(default_factory=list)
    false_negatives: List[FalseNegative] = Field(default_factory=list)


# ============================================================================
# Results and Configuration Models (Subtask 2.3)
# ============================================================================


class EvaluationResult(BaseModel):
    """
    Complete evaluation result for a single dataset.

    Attributes:
        dataset_name: Name of the evaluated dataset
        timestamp: When the evaluation was performed
        session_id: Unique session identifier
        program_id: Schema program ID used
        core_id: Schema core ID used
        error_rate: Error rate of the dataset
        accuracy_metrics: Accuracy and detection metrics
        performance_metrics: Timing and throughput metrics
        confidence_metrics: Confidence score analysis
        error_analysis: Detailed error pattern analysis
        node_metrics: Per-node correction metrics (enum correction pipeline)
        total_records: Total number of records processed
        total_ground_truth_errors: Total errors in ground truth
        processor_version: Version of the processor used
        cost_metrics: Aggregate Bedrock cost metrics for the evaluation
    """

    dataset_name: str = Field(..., min_length=1)
    timestamp: datetime
    session_id: str = Field(..., min_length=1)

    # Configuration
    program_id: str = Field(..., min_length=1)
    core_id: str = Field(..., min_length=1)
    error_rate: float = Field(..., ge=0.0, le=1.0)

    # Metrics
    accuracy_metrics: AccuracyMetrics
    performance_metrics: PerformanceMetrics
    confidence_metrics: ConfidenceMetrics
    error_analysis: ErrorAnalysis
    node_metrics: Dict[str, NodeMetrics] = Field(
        default_factory=dict, description="Per-node correction metrics for enum correction pipeline"
    )

    # Metadata
    total_records: int = Field(..., ge=0)
    total_ground_truth_errors: int = Field(..., ge=0)
    processor_version: str = Field(default="unknown")

    # Cost metrics
    cost_metrics: Optional[CostMetrics] = Field(None, description="Aggregate Bedrock cost metrics for the evaluation")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BatchEvaluationResult(BaseModel):
    """
    Aggregated results from evaluating multiple datasets.

    Attributes:
        batch_id: Unique identifier for this batch run
        timestamp: When the batch evaluation was performed
        datasets: List of individual evaluation results
        average_precision: Mean precision across all datasets
        average_recall: Mean recall across all datasets
        average_f1: Mean F1 score across all datasets
        best_performing_dataset: Name of dataset with highest F1 score
        worst_performing_dataset: Name of dataset with lowest F1 score
        error_rate_correlation: Correlation between error rate and accuracy
        aggregated_field_metrics: Per-field metrics aggregated across all datasets
    """

    batch_id: str = Field(..., min_length=1)
    timestamp: datetime
    datasets: List[EvaluationResult] = Field(..., min_length=1)

    # Aggregate metrics
    average_precision: float = Field(..., ge=0.0, le=1.0)
    average_recall: float = Field(..., ge=0.0, le=1.0)
    average_f1: float = Field(..., ge=0.0, le=1.0)

    # Comparative analysis
    best_performing_dataset: str = Field(..., min_length=1)
    worst_performing_dataset: str = Field(..., min_length=1)
    error_rate_correlation: float = Field(..., ge=-1.0, le=1.0)

    # Aggregated field-level metrics across all datasets
    aggregated_field_metrics: Dict[str, FieldMetrics] = Field(
        default_factory=dict, description="Field metrics aggregated across all datasets in the batch"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BedrockPricingConfig(BaseModel):
    """
    Pricing configuration for AWS Bedrock models.

    Attributes:
        llm_models: Dictionary mapping LLM model IDs to pricing info
                   (input_price_per_1k and output_price_per_1k in USD)
        embedding_models: Dictionary mapping embedding model IDs to price per 1k tokens in USD
    """

    llm_models: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {"amazon.nova-pro-v1:0": {"input_price_per_1k": 0.0008, "output_price_per_1k": 0.0032}},
        description="LLM model pricing (per 1000 tokens)",
    )

    embedding_models: Dict[str, float] = Field(
        default_factory=lambda: {"amazon.titan-embed-text-v2:0": 0.00002},
        description="Embedding model pricing (per 1000 tokens)",
    )

    @model_validator(mode="after")
    def validate_pricing_values(self) -> "BedrockPricingConfig":
        """
        Validate that all pricing values are non-negative.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If any pricing value is negative
        """
        # Validate LLM model pricing
        for model_id, pricing in self.llm_models.items():
            if "input_price_per_1k" in pricing:
                if pricing["input_price_per_1k"] < 0:
                    raise ValueError(
                        f"LLM model '{model_id}' has negative input_price_per_1k: " f"{pricing['input_price_per_1k']}"
                    )
            if "output_price_per_1k" in pricing:
                if pricing["output_price_per_1k"] < 0:
                    raise ValueError(
                        f"LLM model '{model_id}' has negative output_price_per_1k: " f"{pricing['output_price_per_1k']}"
                    )

        # Validate embedding model pricing
        for model_id, price in self.embedding_models.items():
            if price < 0:
                raise ValueError(f"Embedding model '{model_id}' has negative price: {price}")

        return self

    @classmethod
    def from_yaml(cls, path: Path) -> "BedrockPricingConfig":
        """
        Load pricing configuration from a YAML file.

        Args:
            path: Path to the YAML pricing configuration file

        Returns:
            BedrockPricingConfig instance with loaded pricing

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the YAML is malformed or contains invalid values
        """
        import yaml

        if not path.exists():
            raise FileNotFoundError(f"Pricing configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in pricing config {path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Pricing config must be a dictionary, got {type(data).__name__}")

        return cls(**data)


class EvaluationConfig(BaseModel):
    """
    Configuration for evaluation runs.

    Attributes:
        processor_config_path: Path to processor configuration file
        data_directory: Directory containing test datasets
        schema_program_id: Schema program ID to use
        schema_core_id: Schema core ID to use
        output_directory: Where to save evaluation results
        report_formats: List of report formats to generate
        include_visualizations: Whether to include text visualizations
        confidence_threshold: Threshold for high/low confidence classification
        verbose_logging: Enable verbose logging output
        bedrock_pricing: Bedrock model pricing configuration
    """

    # Processor configuration
    processor_config_path: Path = Field(..., description="Path to processor config")

    # Dataset configuration
    data_directory: Path = Field(..., description="Directory with test datasets")
    schema_program_id: str = Field(..., min_length=1)
    schema_core_id: str = Field(..., min_length=1)

    # Output configuration
    output_directory: Path = Field(default=Path("evaluation_results"), description="Output directory for results")
    report_formats: List[str] = Field(default=["json", "markdown"], description="Report formats to generate")

    # Evaluation options
    include_visualizations: bool = Field(default=True, description="Include text-based visualizations")
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Threshold for confidence classification"
    )
    verbose_logging: bool = Field(default=False, description="Enable verbose logging")

    # Pricing configuration
    bedrock_pricing: BedrockPricingConfig = Field(
        default_factory=BedrockPricingConfig, description="Bedrock model pricing configuration"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_yaml(cls, path: Path) -> "EvaluationConfig":
        """
        Load configuration from a YAML file with validation.

        This method:
        1. Validates the file exists and is readable
        2. Parses YAML with error handling
        3. Validates required fields are present
        4. Converts string paths to Path objects
        5. Applies defaults for optional fields
        6. Validates field values and types

        Args:
            path: Path to the YAML configuration file

        Returns:
            EvaluationConfig instance with validated settings

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the YAML is malformed or contains invalid values

        Examples:
            >>> config = EvaluationConfig.from_yaml(Path("config.yaml"))
            >>> print(config.schema_program_id)
            'cyclospora_program'
        """
        import yaml

        # Validate file exists
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}\n"
                f"Please create a config.yaml file or use config.yaml.example as a template."
            )

        # Validate file is readable
        if not path.is_file():
            raise ValueError(f"Configuration path is not a file: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid YAML syntax in config file {path}:\n{e}\n" f"Please check the file for syntax errors."
            ) from e
        except Exception as e:
            raise ValueError(f"Error reading config file {path}: {e}") from e

        # Validate data is a dictionary
        if not isinstance(data, dict):
            raise ValueError(f"Configuration file must contain a YAML dictionary, got {type(data).__name__}")

        # Validate required fields are present
        required_fields = ["processor_config_path", "data_directory", "schema_program_id", "schema_core_id"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(
                f"Missing required configuration fields: {', '.join(missing_fields)}\n"
                f"Required fields: {', '.join(required_fields)}"
            )

        # Convert string paths to Path objects
        path_fields = ["processor_config_path", "data_directory", "output_directory"]
        for field in path_fields:
            if field in data and isinstance(data[field], str):
                data[field] = Path(data[field])

        # Validate schema IDs are non-empty strings
        for field in ["schema_program_id", "schema_core_id"]:
            if field in data:
                if not isinstance(data[field], str):
                    raise ValueError(f"{field} must be a string, got {type(data[field]).__name__}")
                if not data[field].strip():
                    raise ValueError(f"{field} cannot be empty")

        # Validate report_formats if present
        if "report_formats" in data:
            if not isinstance(data["report_formats"], list):
                raise ValueError(f"report_formats must be a list, got {type(data['report_formats']).__name__}")
            valid_formats = {"json", "markdown"}
            invalid_formats = [fmt for fmt in data["report_formats"] if fmt not in valid_formats]
            if invalid_formats:
                raise ValueError(
                    f"Invalid report formats: {', '.join(invalid_formats)}. "
                    f"Valid formats: {', '.join(valid_formats)}"
                )

        # Validate confidence_threshold if present
        if "confidence_threshold" in data:
            threshold = data["confidence_threshold"]
            if not isinstance(threshold, (int, float)):
                raise ValueError(f"confidence_threshold must be a number, got {type(threshold).__name__}")
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"confidence_threshold must be between 0.0 and 1.0, got {threshold}")

        # Create and return config instance
        try:
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Error creating configuration: {e}") from e

    @classmethod
    def from_defaults(cls) -> "EvaluationConfig":
        """
        Create configuration with sensible defaults.

        Returns:
            EvaluationConfig instance with default values
        """
        return cls(
            processor_config_path=Path("projects/metadata-harmonization-processor/config.yaml"),
            data_directory=Path("data/synthetic_dataset"),
            schema_program_id="887f963b-ffea-4f3d-b2b3-9782a97066dc",
            schema_core_id="f2433d87-1984-423e-8a29-5f356cfb8c71",
        )
