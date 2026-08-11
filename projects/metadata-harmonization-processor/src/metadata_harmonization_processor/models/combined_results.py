# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Combined results model for metadata harmonization processing.

This module implements the CombinedResults class that contains both
validation results and schema alignment results in a unified structure
for storage and retrieval.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .change_tracking import ChangeTrackingResults
from .schema_alignment_results import SchemaAlignmentResults
from .validation import ValidationResults


class CombinedResults(BaseModel):
    """
    Combined results containing both validation and schema alignment data.

    This model provides a unified structure for storing and retrieving both
    validation results and schema alignment results in a single JSON file.
    """

    model_config = ConfigDict(populate_by_name=True)

    validation_results: Optional[ValidationResults] = Field(
        None,
        alias="validationResults",
        description="Validation results instance with error details and summary",
    )
    schema_alignment_results: Optional[SchemaAlignmentResults] = Field(
        None,
        alias="schemaAlignmentResults",
        description="Schema alignment results instance with transformation details",
    )
    change_tracking: Optional[ChangeTrackingResults] = Field(
        None,
        alias="changeTracking",
        description="Change tracking information between versions",
    )

    def has_validation_results(self) -> bool:
        """
        Check if validation results are available.

        Returns:
            True if validation_results is not None
        """
        return self.validation_results is not None

    def has_schema_alignment_results(self) -> bool:
        """
        Check if schema alignment results are available.

        Returns:
            True if schema_alignment_results is not None
        """
        return self.schema_alignment_results is not None

    def has_change_tracking(self) -> bool:
        """
        Check if change tracking results are available.

        Returns:
            True if change_tracking is not None
        """
        return self.change_tracking is not None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization to single results.json file.

        Returns:
            Dictionary representation suitable for JSON storage
        """
        result = {}

        if self.validation_results:
            result["validation_results"] = self.validation_results.model_dump()

        if self.schema_alignment_results:
            result["schema_alignment_results"] = self.schema_alignment_results.to_dict()

        if self.change_tracking:
            result["change_tracking"] = self.change_tracking.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CombinedResults":
        """
        Create from dictionary loaded from JSON storage.

        Args:
            data: Dictionary containing combined results data

        Returns:
            CombinedResults instance
        """
        validation_results = None
        schema_alignment_results = None
        change_tracking = None

        if "validation_results" in data and data["validation_results"]:
            validation_results = ValidationResults(**data["validation_results"])

        if "schema_alignment_results" in data and data["schema_alignment_results"]:
            schema_alignment_results = SchemaAlignmentResults.from_dict(data["schema_alignment_results"])

        if "change_tracking" in data and data["change_tracking"]:
            change_tracking = ChangeTrackingResults.from_dict(data["change_tracking"])

        return cls(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
            change_tracking=change_tracking,
        )
