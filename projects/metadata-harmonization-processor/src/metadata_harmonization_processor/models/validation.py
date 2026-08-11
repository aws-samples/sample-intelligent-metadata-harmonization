# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Validation models for metadata harmonization processing.

This module defines the data structures used to represent validation results,
including error details, summaries, and complete validation outcomes.
"""

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValidationErrorType(str, Enum):
    """Types of validation errors that can occur during metadata processing."""

    REQUIRED_VALUE = "REQUIRED_VALUE"
    INVALID_OPTION = "INVALID_OPTION"
    INVALID_PATTERN = "INVALID_PATTERN"


class CorrectionNodeType(str, Enum):
    """Types of correction nodes that can provide recommendations."""

    VALIDATION = "validation"
    FUZZY_MATCHING = "fuzzy_matching"
    CONTEXTUAL_INFERENCE = "contextual_inference"
    SEMANTIC_PREDICTION = "semantic_prediction"
    LLM_RESOLUTION = "llm_resolution"


class ValidationErrorDetail(BaseModel):
    """Detailed information about a single validation error.

    This model represents a specific validation error found in the metadata,
    including location information, error details, and potential recommendations.
    """

    model_config = ConfigDict(populate_by_name=True)

    row: int = Field(
        ...,
        description="Row number where the error occurred (1-based index, first data row is row 1)",
        ge=1,
    )
    column: str = Field(..., description="Column name where the error occurred", min_length=1)
    current_value: str = Field(..., alias="currentValue", description="The current value that caused the error")
    valid_options: Optional[List[str]] = Field(
        None,
        alias="validOptions",
        description="List of valid options for this field (null for free-form fields)",
    )
    recommended_value: Optional[str] = Field(
        None,
        alias="recommendedValue",
        description="Recommended replacement value (null when no recommendation available)",
    )
    error_type: ValidationErrorType = Field(..., alias="errorType", description="Type of validation error")
    error_message: Optional[str] = Field(
        None,
        alias="errorMessage",
        description="Custom error message from schema definition (null when not available)",
    )
    schema_field_name: Optional[str] = Field(
        None,
        alias="schemaFieldName",
        description="Schema field name that caused the error (null when not available)",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        alias="confidenceScore",
        description="Numerical confidence score between 0.0 and 1.0 for the recommended value",
        ge=0.0,
        le=1.0,
    )
    confidence_level: Optional[Literal["High", "Medium", "Low"]] = Field(
        default=None,
        alias="confidenceLevel",
        description="Human-readable confidence level: High, Medium, or Low",
    )
    correction_node: Optional[CorrectionNodeType] = Field(
        None,
        alias="correctionNode",
        description="Name of the node that provided the recommendation (null when no recommendation)",
    )

    @field_validator("confidence_level", mode="before")
    @classmethod
    def normalize_confidence_level(cls, v):
        """Normalize confidence level to capitalized format for backward compatibility.

        Accepts both lowercase ('high', 'medium', 'low') and capitalized ('High', 'Medium', 'Low')
        formats, always returning the capitalized version to maintain consistency.
        """
        if v is None:
            return v

        if isinstance(v, str):
            # Capitalize first letter to normalize format
            return v.capitalize()

        return v

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage and serialization."""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationErrorDetail":
        """Create from dictionary loaded from storage."""
        return cls.model_validate(data)


class ValidationResultsSummary(BaseModel):
    """Summary statistics for validation results.

    This model provides aggregate information about the validation process,
    including total counts and error type breakdowns.
    """

    model_config = ConfigDict(populate_by_name=True)

    total_rows: int = Field(..., alias="totalRows", description="Total number of rows processed", ge=0)
    total_errors: int = Field(
        ...,
        alias="totalErrors",
        description="Total number of validation errors found",
        ge=0,
    )
    error_types: Dict[ValidationErrorType, int] = Field(..., alias="errorTypes", description="Count of errors by type")
    columns_validated: int = Field(
        ...,
        alias="columnsValidated",
        description="Number of columns that were validated",
        ge=0,
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage and serialization."""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationResultsSummary":
        """Create from dictionary loaded from storage."""
        return cls.model_validate(data)


class ValidationResults(BaseModel):
    """Complete validation results structure.

    This model contains the complete set of validation results including
    individual error details and summary statistics. This structure is
    typically stored in S3 as JSON and returned by the API.
    """

    model_config = ConfigDict(populate_by_name=True)

    validation_results: List[ValidationErrorDetail] = Field(
        ...,
        alias="validationResults",
        description="List of all validation errors found",
    )
    summary: ValidationResultsSummary = Field(..., description="Summary statistics for the validation")

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage and serialization."""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationResults":
        """Create from dictionary loaded from storage."""
        return cls.model_validate(data)
