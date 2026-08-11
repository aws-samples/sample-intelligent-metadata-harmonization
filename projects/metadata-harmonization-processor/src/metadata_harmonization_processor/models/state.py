# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
ProcessorState model for managing state between processing stages.

This module contains the ProcessorState Pydantic model that is passed between
AWS Strands nodes to maintain processing state and intermediate results.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from .combined_results import CombinedResults


class NodeTokenUsage(BaseModel):
    """
    Aggregated token usage for a correction node.

    This model tracks token usage from AWS Bedrock API calls made by
    individual correction nodes during metadata processing.
    """

    node_name: str = Field(description="Name of the correction node")
    llm_model_id: Optional[str] = Field(
        default=None,
        description="Model ID used for LLM calls (e.g., 'anthropic.claude-3-5-sonnet-20241022-v2:0')",
    )
    embedding_model_id: Optional[str] = Field(
        default=None,
        description="Model ID used for embedding calls (e.g., 'amazon.titan-embed-text-v2:0')",
    )
    llm_calls: int = Field(default=0, ge=0, description="Number of LLM API calls made")
    llm_input_tokens: int = Field(default=0, ge=0, description="Total input tokens for LLM calls")
    llm_output_tokens: int = Field(default=0, ge=0, description="Total output tokens for LLM calls")
    embedding_calls: int = Field(default=0, ge=0, description="Number of embedding API calls made")
    embedding_tokens: int = Field(default=0, ge=0, description="Total tokens for embedding calls")


class ProcessorState(BaseModel):
    """
    State object passed between AWS Strands nodes during metadata processing.

    This model maintains all processing state including input data, intermediate
    results, and processing metadata. It supports pandas DataFrame objects
    through arbitrary_types_allowed configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    # Input data
    metadata_df: Optional[pd.DataFrame] = Field(
        None, alias="metadataDf", description="Input metadata DataFrame to be processed"
    )
    program_id: Optional[str] = Field(None, alias="programId", description="Schema program identifier for validation")
    core_id: Optional[str] = Field(None, alias="coreId", description="Schema core identifier for validation")

    # Intermediate results
    aligned_df: Optional[pd.DataFrame] = Field(
        None,
        alias="alignedDf",
        description="Schema-aligned DataFrame after column mapping",
    )
    schema_definition: Optional[Dict[str, Any]] = Field(
        None,
        alias="schemaDefinition",
        description="Retrieved schema definition used for validation",
    )

    # Final results
    combined_results: Optional[CombinedResults] = Field(
        None,
        alias="combinedResults",
        description="Combined validation and schema alignment results",
    )

    # Processing metadata
    job_id: str = Field(
        default="",
        alias="jobId",
        description="Unique job identifier for tracking processing session",
    )
    current_stage: str = Field(default="", alias="currentStage", description="Current processing stage name")
    processing_start_time: Optional[datetime] = Field(
        None,
        alias="processingStartTime",
        description="Timestamp when processing started",
    )

    # Processing metadata for schema alignment (temporary for processing)
    column_mappings: Optional[Dict[str, str]] = Field(
        None,
        alias="columnMappings",
        description="Mapping of original column names to aligned column names (temporary for processing)",
    )
    transformation_summary: Optional[Dict[str, Any]] = Field(
        None,
        alias="transformationSummary",
        description="Summary of transformations applied during schema alignment (temporary for processing)",
    )

    # Token usage tracking for cost estimation
    token_usage: Dict[str, NodeTokenUsage] = Field(
        default_factory=dict,
        alias="tokenUsage",
        description="Token usage by correction node (e.g., 'llm_resolution', 'semantic_prediction')",
    )

    def set_current_stage(self, stage: str) -> None:
        """
        Update the current processing stage.

        Args:
            stage: Name of the current processing stage
        """
        self.current_stage = stage

    def has_metadata(self) -> bool:
        """
        Check if the state contains input metadata.

        Returns:
            True if metadata_df is not None and not empty
        """
        return self.metadata_df is not None and not self.metadata_df.empty

    def has_schema_ids(self) -> bool:
        """
        Check if the state contains both required schema identifiers.

        Returns:
            True if both program_id and core_id are set
        """
        return self.program_id is not None and self.core_id is not None

    def has_aligned_data(self) -> bool:
        """
        Check if the state contains aligned DataFrame.

        Returns:
            True if aligned_df is not None and not empty
        """
        return self.aligned_df is not None and not self.aligned_df.empty

    def has_validation_results(self) -> bool:
        """
        Check if the state contains validation results.

        Returns:
            True if combined_results contains validation_results
        """
        return self.combined_results is not None and self.combined_results.has_validation_results()

    def has_schema_alignment_results(self) -> bool:
        """
        Check if the state contains schema alignment results.

        Returns:
            True if combined_results contains schema_alignment_results
        """
        return self.combined_results is not None and self.combined_results.has_schema_alignment_results()

    def get_combined_results(self) -> Optional[CombinedResults]:
        """
        Get combined results instance for unified storage.

        Returns:
            CombinedResults instance or None if not available
        """
        return self.combined_results

    def get_processing_duration(self) -> Optional[float]:
        """
        Calculate processing duration in seconds.

        Returns:
            Duration in seconds if processing_start_time is set, None otherwise
        """
        if self.processing_start_time is None:
            return None
        return (datetime.now() - self.processing_start_time).total_seconds()
