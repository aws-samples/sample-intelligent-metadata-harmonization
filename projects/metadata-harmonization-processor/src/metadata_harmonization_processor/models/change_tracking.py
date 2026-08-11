# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Change tracking models for metadata harmonization processing.

This module implements the change tracking data models that capture
differences between versions of processing results, including detailed
change objects, summaries, and tracking metadata.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChangeObject(BaseModel):
    """
    Represents a single change between versions.

    This model captures detailed information about a specific change,
    including the type of change, source, location, and values.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
    )

    change_id: str = Field(
        default_factory=lambda: f"chg_{uuid.uuid4().hex[:8]}",
        alias="changeId",
        description="Unique identifier for this change",
    )
    change_type: Literal["add", "remove", "rename"] = Field(
        ..., alias="changeType", description="Type of change operation"
    )
    source_type: Literal["system", "user"] = Field(..., alias="sourceType", description="Source of the change")
    component: Literal["validation", "schema_alignment"] = Field(..., description="Component where change occurred")

    # Location information
    row: Optional[int] = Field(
        None,
        description="Row number where the change occurred (1-based index, first data row is row 1, None for schema-level changes)",
        ge=1,
    )
    column: str = Field(..., description="Column name where the error occurred", min_length=1)

    # Change details
    old_value: Optional[Union[str, int, float, bool]] = Field(
        None, alias="oldValue", description="Previous value (for rename/remove)"
    )
    new_value: Optional[Union[str, int, float, bool]] = Field(
        None, alias="newValue", description="New value (for add/rename)"
    )

    # Metadata
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp when change was detected",
    )
    source_version: int = Field(..., alias="sourceVersion", description="Version number of the source", ge=1)
    target_version: int = Field(..., alias="targetVersion", description="Version number of the target", ge=1)

    # Additional context
    confidence_score: Optional[float] = Field(
        None,
        alias="confidenceScore",
        description="Confidence score if system-generated",
        ge=0.0,
        le=1.0,
    )
    user_context: Optional[Dict[str, Any]] = Field(None, alias="userContext", description="Additional user context")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        """Validate that timestamp is a valid ISO-8601 format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("timestamp must be in ISO-8601 format")

    @model_validator(mode="after")
    def validate_version_sequence(self):
        """Validate that target_version is greater than source_version."""
        if self.target_version <= self.source_version:
            raise ValueError("target_version must be greater than source_version")
        return self

    @model_validator(mode="after")
    def validate_change_values(self):
        """Validate that change values are consistent with change type."""
        if self.change_type == "add":
            if self.old_value is not None:
                raise ValueError("'add' changes should not have old_value")
            if self.new_value is None:
                raise ValueError("'add' changes must have new_value")
        elif self.change_type == "remove":
            if self.old_value is None:
                raise ValueError("'remove' changes must have old_value")
            if self.new_value is not None:
                raise ValueError("'remove' changes should not have new_value")
        elif self.change_type == "rename":
            if self.old_value is None or self.new_value is None:
                raise ValueError("'rename' changes must have both old_value and new_value")
            if self.old_value == self.new_value:
                raise ValueError("'rename' changes must have different old_value and new_value")

        return self

    @model_validator(mode="after")
    def validate_location_info(self):
        """Validate location information based on component type."""
        # For validation changes, row must be provided
        if self.component == "validation" and self.row is None:
            raise ValueError("Row must be provided for validation component changes")

        # Column is always required
        if not self.column or not self.column.strip():
            raise ValueError("Column must be provided for all changes")

        return self

    @model_validator(mode="after")
    def validate_confidence_score_context(self):
        """Validate confidence score is only present for system changes."""
        if self.confidence_score is not None and self.source_type != "system":
            raise ValueError("confidence_score should only be present for system changes")

        return self


class ChangesSummary(BaseModel):
    """
    Summary statistics for changes.

    This model provides aggregated counts and statistics about
    the changes detected between versions.
    """

    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    total_changes: int = Field(0, alias="totalChanges", description="Total number of changes", ge=0)
    adds: int = Field(0, description="Number of additions", ge=0)
    removes: int = Field(0, description="Number of removals", ge=0)
    renames: int = Field(0, description="Number of renames/modifications", ge=0)
    system_changes: int = Field(0, alias="systemChanges", description="Number of system-generated changes", ge=0)
    user_changes: int = Field(0, alias="userChanges", description="Number of user-generated changes", ge=0)

    @model_validator(mode="after")
    def validate_totals(self):
        """Validate that totals are consistent."""
        # Validate that total_changes equals sum of change types
        expected_total = self.adds + self.removes + self.renames
        if self.total_changes != expected_total:
            raise ValueError(
                f"total_changes ({self.total_changes}) must equal sum of adds + removes + renames ({expected_total})"
            )

        # Validate that system_changes + user_changes equals total_changes
        if self.system_changes + self.user_changes != self.total_changes:
            raise ValueError(
                f"system_changes ({self.system_changes}) + user_changes ({self.user_changes}) "
                f"must equal total_changes ({self.total_changes})"
            )

        return self

    @classmethod
    def from_changes(cls, changes: List[ChangeObject]) -> "ChangesSummary":
        """
        Create summary from a list of change objects.

        Args:
            changes: List of ChangeObject instances

        Returns:
            ChangesSummary instance with calculated statistics
        """
        adds = sum(1 for change in changes if change.change_type == "add")
        removes = sum(1 for change in changes if change.change_type == "remove")
        renames = sum(1 for change in changes if change.change_type == "rename")

        system_changes = sum(1 for change in changes if change.source_type == "system")
        user_changes = sum(1 for change in changes if change.source_type == "user")

        return cls(
            total_changes=len(changes),
            adds=adds,
            removes=removes,
            renames=renames,
            system_changes=system_changes,
            user_changes=user_changes,
        )


class ChangeTrackingResults(BaseModel):
    """
    Container for change tracking information.

    This model contains all change tracking data including individual
    changes, summary statistics, and comparison metadata.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
    )

    changes: List[ChangeObject] = Field(default_factory=list, description="List of detected changes")
    summary: ChangesSummary = Field(..., description="Summary of changes")
    comparison_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        alias="comparisonMetadata",
        description="Metadata about the comparison",
    )

    @model_validator(mode="after")
    def validate_summary_consistency(self):
        """Validate that summary is consistent with changes list."""
        # Create expected summary from changes
        expected_summary = ChangesSummary.from_changes(self.changes)

        # Check if provided summary matches expected
        if (
            self.summary.total_changes != expected_summary.total_changes
            or self.summary.adds != expected_summary.adds
            or self.summary.removes != expected_summary.removes
            or self.summary.renames != expected_summary.renames
            or self.summary.system_changes != expected_summary.system_changes
            or self.summary.user_changes != expected_summary.user_changes
        ):
            raise ValueError("Summary statistics do not match the changes list")

        return self

    @classmethod
    def create_from_changes(
        cls,
        changes: List[ChangeObject],
        comparison_metadata: Optional[Dict[str, Any]] = None,
    ) -> "ChangeTrackingResults":
        """
        Create change tracking results from a list of changes.

        Args:
            changes: List of ChangeObject instances
            comparison_metadata: Optional metadata about the comparison

        Returns:
            ChangeTrackingResults instance with auto-generated summary
        """
        summary = ChangesSummary.from_changes(changes)

        if comparison_metadata is None:
            comparison_metadata = {
                "detection_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_changes_detected": len(changes),
            }

        return cls(changes=changes, summary=summary, comparison_metadata=comparison_metadata)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON storage
        """
        return {
            "changes": [change.model_dump() for change in self.changes],
            "summary": self.summary.model_dump(),
            "comparison_metadata": self.comparison_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeTrackingResults":
        """
        Create from dictionary loaded from JSON storage.

        Args:
            data: Dictionary containing change tracking data

        Returns:
            ChangeTrackingResults instance
        """
        changes = [ChangeObject(**change_data) for change_data in data.get("changes", [])]
        summary = ChangesSummary(**data.get("summary", {}))
        comparison_metadata = data.get("comparison_metadata", {})

        return cls(changes=changes, summary=summary, comparison_metadata=comparison_metadata)
