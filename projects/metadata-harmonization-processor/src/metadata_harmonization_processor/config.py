# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Configuration management for the metadata harmonization processor.

This module contains the ProcessorConfig class and configuration
loading functions using Pydantic Settings with YAML support.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from loguru import logger
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class ConfidenceConfig(BaseSettings):
    """Configuration for confidence scoring algorithms."""

    # Global confidence settings
    enabled: bool = Field(default=True, description="Enable/disable confidence scoring")

    # Confidence level mapping (level -> numerical score)
    confidence_level_mapping: Dict[str, float] = Field(
        default={"High": 0.9, "Medium": 0.65, "Low": 0.3},
        description="Mapping from confidence levels to numerical scores",
    )

    # Prediction confidence thresholds for semantic similarity
    semantic_high_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Threshold for high confidence in semantic similarity",
    )
    semantic_medium_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Threshold for medium confidence in semantic similarity",
    )

    # Prediction confidence thresholds for pattern matching
    pattern_high_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Threshold for high confidence in pattern matching",
    )
    pattern_medium_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Threshold for medium confidence in pattern matching",
    )

    # Schema alignment confidence settings
    schema_confidence_enabled: bool = Field(default=True, description="Enable confidence scoring for schema alignment")
    llm_confidence_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for LLM confidence in schema alignment scoring",
    )
    similarity_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for similarity score in schema alignment scoring",
    )

    # Prediction confidence settings
    prediction_confidence_enabled: bool = Field(
        default=True,
        description="Enable confidence scoring for validation error predictions",
    )

    model_config = {
        "env_prefix": "CONFIDENCE_",
        "case_sensitive": False,
        "extra": "forbid",
    }

    @field_validator("confidence_level_mapping")
    @classmethod
    def validate_confidence_mapping(cls, v):
        """Validate confidence level mapping."""
        if not isinstance(v, dict):
            raise ValueError("confidence_level_mapping must be a dictionary")

        required_levels = {"High", "Medium", "Low"}
        provided_levels = set(v.keys())

        if not required_levels.issubset(provided_levels):
            missing = required_levels - provided_levels
            raise ValueError(f"confidence_level_mapping missing required levels: {missing}")

        for level, score in v.items():
            if not isinstance(score, (int, float)):
                raise ValueError(f"confidence_level_mapping['{level}'] must be a number")
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"confidence_level_mapping['{level}'] must be between 0.0 and 1.0")

        return v

    @model_validator(mode="after")
    def validate_confidence_settings(self):
        """Validate confidence configuration settings."""
        # Skip validation if confidence is disabled
        if not self.enabled:
            return self

        # Validate semantic threshold ordering
        if self.semantic_medium_threshold >= self.semantic_high_threshold:
            raise ValueError("semantic_medium_threshold must be less than semantic_high_threshold")

        # Validate pattern threshold ordering
        if self.pattern_medium_threshold >= self.pattern_high_threshold:
            raise ValueError("pattern_medium_threshold must be less than pattern_high_threshold")

        # Validate weight sum
        total = self.llm_confidence_weight + self.similarity_weight
        if abs(total - 1.0) > 0.001:  # Allow small floating point errors
            raise ValueError(f"llm_confidence_weight + similarity_weight must equal 1.0, got {total}")

        return self


class SchemaAlignmentConfig(BaseSettings):
    """Configuration for schema alignment processing with LLM support."""

    # LLM Configuration
    use_llm: bool = Field(default=True, description="Enable/disable LLM matching")
    model_id: str = Field(default="amazon.nova-pro-v1:0", description="Bedrock model configuration")
    aws_region: str = Field(default="us-east-1", description="Bedrock client region")
    llm_temperature: float = Field(default=0.3, description="LLM inference temperature")
    llm_max_tokens: int = Field(default=800, description="LLM response token limit")
    llm_timeout_seconds: int = Field(default=30, description="LLM request timeout")
    fallback_on_llm_failure: bool = Field(default=True, description="Automatic fallback to rule-based matching")

    # Rule-based Configuration
    similarity_threshold: float = Field(default=0.7, description="Rule-based matching threshold")

    # Change Tracking Configuration
    enable_change_tracking: bool = Field(default=True, description="Change detection configuration")

    # Column Matching Configuration
    enable_column_batching: bool = Field(
        default=False,
        description="Enable batching for column matching with large schemas",
    )
    column_batch_size: int = Field(
        default=20,
        description="Number of columns to process per LLM batch for column matching",
    )

    # Column Transformation Configuration
    enable_column_splitting: bool = Field(
        default=True,
        description="Enable automatic column splitting (e.g., Full Name → First Name + Last Name)",
    )
    enable_column_combining: bool = Field(
        default=True,
        description="Enable automatic column combining (e.g., First Name + Last Name → Full Name)",
    )

    model_config = {
        "env_prefix": "SCHEMA_ALIGNMENT_",
        "case_sensitive": False,
        "extra": "forbid",
    }

    @field_validator("column_batch_size")
    @classmethod
    def validate_column_batch_size(cls, v):
        """Validate column batch size."""
        if v <= 0:
            raise ValueError("column_batch_size must be positive")
        return v

    @model_validator(mode="after")
    def validate_column_settings(self):
        """Validate column configuration settings."""
        if self.use_llm and self.column_batch_size <= 0:
            raise ValueError("column_batch_size must be positive when LLM is enabled")

        return self


class SemanticPredictionConfig(BaseSettings):
    """Configuration for semantic prediction processing."""

    # Concurrency Configuration
    max_concurrent_predictions: int = Field(
        default=50,
        ge=1,
        description="Maximum number of concurrent semantic predictions (semaphore limit)",
    )

    # Similarity Configuration
    cosine_similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Threshold for cosine similarity matching",
    )

    # Embedding Model Configuration
    embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock embedding model ID to use",
    )

    embedding_provider: Literal["bedrock", "sagemaker"] = Field(
        default="bedrock", description="Embedding provider (bedrock or sagemaker)"
    )

    model_config = {
        "env_prefix": "SEMANTIC_PREDICTION_",
        "case_sensitive": False,
        "extra": "forbid",
    }


class NodeConfig(BaseSettings):
    """Configuration for a single processing node in the pipeline."""

    name: str = Field(..., description="Node name (must match registry key)")
    enabled: bool = Field(default=True, description="Whether this node is enabled")

    model_config = {"extra": "forbid"}


class EnumCorrectionPipelineConfig(BaseSettings):
    """Configuration for enum correction pipeline."""

    enabled: bool = Field(default=True, description="Enable/disable the enum correction pipeline")

    nodes: List[NodeConfig] = Field(
        default=[
            NodeConfig(name="fuzzy_matching", enabled=True),
            NodeConfig(name="contextual_inference", enabled=True),
            NodeConfig(name="semantic_prediction", enabled=True),
            NodeConfig(name="llm_resolution", enabled=True),
        ],
        description="Ordered list of correction nodes to execute",
    )

    model_config = {
        "env_prefix": "ENUM_CORRECTION_PIPELINE_",
        "case_sensitive": False,
        "extra": "forbid",
    }

    @field_validator("nodes")
    @classmethod
    def validate_node_names(cls, v):
        """Validate that node names are valid."""
        valid_names = {
            "fuzzy_matching",
            "contextual_inference",
            "semantic_prediction",
            "llm_resolution",
        }
        for node in v:
            if node.name not in valid_names:
                raise ValueError(f"Invalid node name: {node.name}. " f"Must be one of {valid_names}")
        return v


class FuzzyMatchingConfig(BaseSettings):
    """Configuration for fuzzy matching node."""

    min_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for accepting fuzzy match (0.0-1.0)",
    )

    max_concurrent_predictions: int = Field(
        default=50,
        ge=1,
        description="Maximum number of concurrent fuzzy matching operations",
    )

    model_config = {
        "env_prefix": "FUZZY_MATCHING_",
        "case_sensitive": False,
        "extra": "forbid",
    }


class ContextualInferenceConfig(BaseSettings):
    """Configuration for contextual inference node."""

    k_neighbors: int = Field(
        default=5,
        ge=1,
        description="Number of nearest neighbors to consider (k in k-NN)",
    )

    similarity_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="Weight for similarity-based scoring")

    cooccurrence_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for co-occurrence-based scoring",
    )

    min_confidence_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for accepting recommendation (0.0-1.0)",
    )

    max_concurrent_predictions: int = Field(
        default=50,
        ge=1,
        description="Maximum number of concurrent contextual inference operations",
    )

    exclude_column_patterns: List[str] = Field(
        default=[],
        description="Regex patterns to exclude columns from feature extraction (e.g., '.*_id$' to exclude ID columns)",
    )

    model_config = {
        "env_prefix": "CONTEXTUAL_INFERENCE_",
        "case_sensitive": False,
        "extra": "forbid",
    }

    @field_validator("exclude_column_patterns")
    @classmethod
    def validate_regex_patterns(cls, v):
        """Validate that all patterns are valid regex."""
        import re

        if not isinstance(v, list):
            raise ValueError("exclude_column_patterns must be a list")

        for pattern in v:
            if not isinstance(pattern, str):
                raise ValueError(f"Pattern must be a string, got {type(pattern)}")
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

        return v

    @model_validator(mode="after")
    def validate_weights(self):
        """Validate that similarity_weight + cooccurrence_weight = 1.0"""
        total = self.similarity_weight + self.cooccurrence_weight
        if abs(total - 1.0) > 0.001:  # Allow small floating point errors
            raise ValueError(f"similarity_weight + cooccurrence_weight must equal 1.0, got {total}")
        return self


class LLMResolutionConfig(BaseSettings):
    """Configuration for LLM resolution node."""

    model_id: str = Field(
        default="amazon.nova-pro-v1:0",
        description="Bedrock model ID to use for LLM resolution",
    )

    aws_region: str = Field(default="us-east-1", description="AWS region for Bedrock service")

    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="LLM inference temperature")

    max_tokens: int = Field(default=500, ge=1, description="Maximum tokens in LLM response")

    timeout_seconds: int = Field(default=30, ge=1, description="Timeout for LLM requests in seconds")

    min_confidence_level: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Minimum confidence level required (low/medium/high)",
    )

    max_concurrent_predictions: int = Field(default=10, ge=1, description="Maximum number of concurrent LLM operations")

    max_retries: int = Field(default=3, ge=1, description="Maximum number of retry attempts for LLM calls")

    use_strands_agent: bool = Field(default=True, description="Use Strands agent framework for LLM calls")

    # Internal mapping of confidence levels to numerical thresholds
    _confidence_level_thresholds: Dict[str, float] = {
        "low": 0.5,
        "medium": 0.7,
        "high": 0.85,
    }

    model_config = {
        "env_prefix": "LLM_RESOLUTION_",
        "case_sensitive": False,
        "extra": "forbid",
    }

    def get_threshold(self) -> float:
        """Get numerical threshold for configured confidence level."""
        return self._confidence_level_thresholds[self.min_confidence_level]


class ProcessorConfig(BaseSettings):
    """Pydantic settings for processor configuration."""

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region for services")
    aws_profile: Optional[str] = Field(default=None, description="AWS profile to use")

    # Session Management Configuration (AWS Strands)
    session_saver_type: Literal["s3", "file"] = Field(
        default="s3", description="Type of session manager to use for AWS Strands"
    )
    session_s3_bucket: Optional[str] = Field(
        None,
        description="S3 bucket for state persistence (required if session_saver_type=s3)",
    )
    session_s3_prefix: str = Field(default="sessions/", description="S3 prefix for session files")
    file_session_directory: Optional[str] = Field(
        None,
        description="Local directory for file-based session storage (required if session_saver_type=file)",
    )

    # Redis Configuration (optional)
    enable_redis_cache: bool = Field(default=True, description="Enable Redis caching for embeddings")
    redis_endpoint: Optional[str] = Field(
        None,
        description="ElastiCache Redis endpoint (required if enable_redis_cache=True)",
    )
    redis_port: int = Field(default=6379, description="Redis port")

    # In-Memory Cache Configuration (fallback when Redis is disabled)
    enable_memory_cache: bool = Field(
        default=True,
        description="Enable in-memory dictionary caching when Redis is disabled",
    )
    memory_cache_max_size: int = Field(
        default=50000,
        description=(
            "Maximum number of embeddings to cache in memory (increased for large schemas). "
            "For large schemas with many enum values (like 1000+ valid options), consider "
            "increasing to 100000+ to maximize cache hits and reduce API calls."
        ),
    )

    # AI Model Configuration (Deprecated - use semantic_prediction config instead)
    embedding_provider: Literal["bedrock", "sagemaker"] = Field(default="bedrock")
    sagemaker_endpoint_name: Optional[str] = Field(default=None)

    # Processing Configuration
    max_retries: int = Field(default=3, description="Maximum number of retries for operations")
    timeout_seconds: int = Field(default=300, description="Timeout for operations in seconds")
    cosine_similarity_threshold: float = Field(default=0.8, description="Threshold for cosine similarity matching")

    # Schema Configuration
    schema_directory: str = Field(..., description="Path to directory containing catalog.json and schema files")

    # Local Development Mode Configuration
    local_development_mode: bool = Field(
        default=False,
        description="Enable local development mode without cloud services",
    )

    # Schema Alignment Configuration
    schema_alignment: SchemaAlignmentConfig = Field(
        default_factory=SchemaAlignmentConfig,
        description="Schema alignment processing configuration",
    )

    # Semantic Prediction Configuration
    semantic_prediction: SemanticPredictionConfig = Field(
        default_factory=SemanticPredictionConfig,
        description="Semantic prediction processing configuration",
    )

    # Enum Correction Pipeline Configuration
    enum_correction_pipeline: EnumCorrectionPipelineConfig = Field(
        default_factory=EnumCorrectionPipelineConfig,
        description="Enum correction pipeline configuration",
    )

    # Fuzzy Matching Configuration
    fuzzy_matching: FuzzyMatchingConfig = Field(
        default_factory=FuzzyMatchingConfig,
        description="Fuzzy matching node configuration",
    )

    # Contextual Inference Configuration
    contextual_inference: ContextualInferenceConfig = Field(
        default_factory=ContextualInferenceConfig,
        description="Contextual inference node configuration",
    )

    # LLM Resolution Configuration
    llm_resolution: LLMResolutionConfig = Field(
        default_factory=LLMResolutionConfig,
        description="LLM resolution node configuration",
    )

    # Confidence Scoring Configuration
    confidence: ConfidenceConfig = Field(
        default_factory=ConfidenceConfig, description="Confidence scoring configuration"
    )

    # Data Saver Configuration
    job_status_saver_type: Literal["dynamodb", "local"] = Field(
        default="dynamodb", description="Type of job status saver to use"
    )
    job_status_table_name: Optional[str] = Field(
        default="metadata-jobs",
        description="DynamoDB table name for job status (required for dynamodb type)",
    )
    job_status_storage_dir: Optional[str] = Field(
        default="./data/job_status",
        description="Local directory for job status files (required for local type)",
    )

    result_saver_type: Literal["s3", "local"] = Field(default="s3", description="Type of result saver to use")
    results_s3_bucket: Optional[str] = Field(
        default=None, description="S3 bucket for storing results (required for s3 type)"
    )
    results_s3_prefix: str = Field(default="validation-results/", description="S3 key prefix for results")
    results_local_dir: str = Field(
        default="./data/validation-results",
        description="Local directory for result files",
    )

    model_config = {
        "env_prefix": "PROCESSOR_",
        "case_sensitive": False,
        "extra": "allow",
    }

    def model_post_init(self, __context: Any) -> None:
        """Validate configuration after initialization."""
        self._validate_session_manager_config()
        self._validate_redis_config()
        self._validate_ai_config()
        self._validate_data_saver_config()
        self._validate_confidence_config()

    def _validate_session_manager_config(self) -> None:
        """Validate session manager configuration."""
        if self.session_saver_type == "s3" and not self.session_s3_bucket:
            raise ValueError("session_s3_bucket is required when session_saver_type is 's3'")

        if self.session_saver_type == "file" and not self.file_session_directory:
            raise ValueError("file_session_directory is required when session_type is 'file'")

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration."""
        if self.enable_redis_cache and not self.redis_endpoint:
            raise ValueError("redis_endpoint is required when enable_redis_cache is True")

    def _validate_ai_config(self) -> None:
        """Validate AI model configuration."""
        # Validate semantic prediction embedding configuration
        if self.semantic_prediction.embedding_provider == "bedrock":
            if not self.semantic_prediction.embedding_model:
                raise ValueError(
                    "semantic_prediction.embedding_model is required when "
                    "semantic_prediction.embedding_provider is 'bedrock'"
                )

        if self.semantic_prediction.embedding_provider == "sagemaker" and not self.sagemaker_endpoint_name:
            raise ValueError("sagemaker_endpoint_name is required when embedding_provider is 'sagemaker'")

    def _validate_data_saver_config(self) -> None:
        """Validate data saver configuration."""
        # Validate job status saver configuration
        if self.job_status_saver_type == "dynamodb" and not self.job_status_table_name:
            raise ValueError("job_status_table_name is required when job_status_saver_type is 'dynamodb'")

        if self.job_status_saver_type == "local" and not self.job_status_storage_dir:
            raise ValueError("job_status_storage_dir is required when job_status_saver_type is 'local'")

        # Validate result saver configuration
        if self.result_saver_type == "s3" and not self.results_s3_bucket:
            raise ValueError("results_s3_bucket is required when result_saver_type is 's3'")

    def _validate_confidence_config(self) -> None:
        """Validate confidence scoring configuration."""
        if not self.confidence.enabled:
            logger.info("Confidence scoring is disabled")
            return

        # Validate threshold ordering
        if self.confidence.semantic_medium_threshold >= self.confidence.semantic_high_threshold:
            raise ValueError(
                f"semantic_medium_threshold ({self.confidence.semantic_medium_threshold}) "
                f"must be less than semantic_high_threshold ({self.confidence.semantic_high_threshold})"
            )

        if self.confidence.pattern_medium_threshold >= self.confidence.pattern_high_threshold:
            raise ValueError(
                f"pattern_medium_threshold ({self.confidence.pattern_medium_threshold}) "
                f"must be less than pattern_high_threshold ({self.confidence.pattern_high_threshold})"
            )

        # Validate weight sum
        weight_sum = self.confidence.llm_confidence_weight + self.confidence.similarity_weight
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"llm_confidence_weight + similarity_weight must equal 1.0, got {weight_sum}")

        # Validate confidence level mapping scores
        for level, score in self.confidence.confidence_level_mapping.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"confidence_level_mapping['{level}'] = {score} must be between 0.0 and 1.0")

        # Validate that High > Medium > Low in the mapping
        high_score = self.confidence.confidence_level_mapping.get("High", 0.0)
        medium_score = self.confidence.confidence_level_mapping.get("Medium", 0.0)
        low_score = self.confidence.confidence_level_mapping.get("Low", 0.0)

        if not (high_score > medium_score > low_score):
            raise ValueError(
                "confidence_level_mapping scores must be ordered: High > Medium > Low. "
                f"Got High={high_score}, Medium={medium_score}, Low={low_score}"
            )

        logger.debug("Confidence configuration validation passed")


def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override values taking precedence.

    Args:
        base: Base dictionary
        override: Override dictionary with values that take precedence

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def resolve_relative_paths(data: Dict[str, Any], config_dir: Path) -> Dict[str, Any]:
    """
    Resolve relative paths in configuration relative to config file location.

    Args:
        data: Configuration data dictionary
        config_dir: Directory containing the config file

    Returns:
        Configuration data with resolved paths
    """
    path_fields = [
        "schema_directory",
        "file_session_directory",
        "job_status_storage_dir",
        "results_local_dir",
    ]

    for field in path_fields:
        if field in data and data[field] is not None:
            path = Path(data[field])
            if not path.is_absolute():
                resolved_path = (config_dir / path).resolve()
                data[field] = str(resolved_path)

    return data


def load_processor_settings(
    config_path: Optional[Path] = None, override: Optional[Dict[str, Any]] = None
) -> ProcessorConfig:
    """
    Load hierarchical processor settings.

    Args:
        config_path: Optional path to configuration YAML file
        override: Optional dictionary of settings to override

    Returns:
        Loaded processor settings with path resolution

    Raises:
        FileNotFoundError: If config_path is provided but file doesn't exist
        yaml.YAMLError: If YAML file is invalid
        ValueError: If configuration validation fails
    """
    if override is None:
        override = {}

    if config_path and config_path.exists():
        logger.debug(f"Loading processor config from: {config_path}")

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in config file {config_path}: {e}")

        # Resolve relative paths relative to config file location
        config_dir = config_path.parent
        data = resolve_relative_paths(data, config_dir)

        # Apply overrides to the loaded data
        data = deep_merge_dicts(data, override)

        logger.info(f"Loaded configuration: {json.dumps(data, indent=2)}")

        try:
            settings = ProcessorConfig(**data)
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")

        logger.debug(f"Final config: {settings.model_dump_json()}")
        return settings

    elif config_path:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # If no config file, create settings with just the overrides
    logger.debug("No config file provided, using overrides only")
    try:
        return ProcessorConfig(**override)
    except Exception as e:
        raise ValueError(f"Configuration validation failed with overrides: {e}")
