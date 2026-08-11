# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Data models for the metadata harmonization processor.

This module contains Pydantic models for validation results, processor state,
and other data structures used throughout the processing pipeline.
"""

from .change_tracking import ChangeObject, ChangesSummary, ChangeTrackingResults
from .combined_results import CombinedResults
from .job import JobResults, MetadataSchema, MetadataUploadJob, ProgramSchema
from .schema_alignment_results import SchemaAlignmentResults
from .state import NodeTokenUsage, ProcessorState
from .validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)

__all__ = [
    "ValidationErrorType",
    "ValidationErrorDetail",
    "ValidationResultsSummary",
    "ValidationResults",
    "ProcessorState",
    "NodeTokenUsage",
    "JobResults",
    "ProgramSchema",
    "MetadataSchema",
    "MetadataUploadJob",
    "SchemaAlignmentResults",
    "CombinedResults",
    "ChangeObject",
    "ChangesSummary",
    "ChangeTrackingResults",
]
