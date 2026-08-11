# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Schema alignment results model for metadata harmonization processing.

This module implements the SchemaAlignmentResults class that contains
the results of schema alignment processing, including detailed change
information and summary statistics.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class SchemaAlignmentChangeDetail(BaseModel):
    """Model for individual schema alignment change details."""

    change_type: str = Field(..., alias="changeType", description="Type of change: 'add', 'remove', 'rename'")
    original_column: str | None = Field(
        None,
        alias="originalColumn",
        description="Original column name (for rename/remove)",
    )
    new_column: str | None = Field(None, alias="newColumn", description="New column name (for rename/add)")
    reason: str | None = Field(None, description="Reason for the change")
    row_count_affected: int | None = Field(
        None,
        alias="rowCountAffected",
        description="Number of rows affected by this change",
    )
    confidence_score: float = Field(
        default=0.0,
        alias="confidenceScore",
        description="Numerical confidence score between 0.0 and 1.0 for the schema alignment change",
        ge=0.0,
        le=1.0,
    )
    confidence_level: str = Field(
        default="Low",
        alias="confidenceLevel",
        description="Human-readable confidence level: High, Medium, or Low",
    )

    model_config = ConfigDict(populate_by_name=True)


class SchemaAlignmentResultsSummary(BaseModel):
    """Model for schema alignment results summary."""

    job_id: str = Field(..., alias="jobId", description="Job identifier")
    version: int = Field(..., description="Version number")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When results were created")

    original_data_csv: str = Field(..., alias="originalDataCsv", description="Original CSV data")
    aligned_data_csv: str = Field(..., alias="alignedDataCsv", description="Schema-aligned CSV data")

    total_changes: int = Field(0, alias="totalChanges", description="Total number of schema changes")
    columns_renamed: int = Field(0, alias="columnsRenamed", description="Number of columns renamed")
    columns_added: int = Field(0, alias="columnsAdded", description="Number of columns added")
    columns_removed: int = Field(0, alias="columnsRemoved", description="Number of columns removed")
    rows_original: int = Field(0, alias="rowsOriginal", description="Number of rows in original data")
    rows_aligned: int = Field(0, alias="rowsAligned", description="Number of rows in aligned data")

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()


class SchemaAlignmentResults(BaseModel):
    """Model for schema alignment results data."""

    schema_alignment_results: list[SchemaAlignmentChangeDetail] = Field(
        default_factory=list,
        alias="schemaAlignmentResults",
        description="List of detailed schema alignment changes",
    )
    summary: SchemaAlignmentResultsSummary = Field(..., description="Summary of schema alignment results")

    model_config = ConfigDict(populate_by_name=True)

    # Backward compatibility properties
    @property
    def job_id(self) -> str:
        """Backward compatibility: access job_id from summary."""
        return self.summary.job_id

    @property
    def version(self) -> int:
        """Backward compatibility: access version from summary."""
        return self.summary.version

    @property
    def timestamp(self) -> datetime:
        """Backward compatibility: access timestamp from summary."""
        return self.summary.timestamp

    @property
    def original_data_csv(self) -> str:
        """Backward compatibility: access original_data_csv from summary."""
        return self.summary.original_data_csv

    @property
    def aligned_data_csv(self) -> str:
        """Backward compatibility: access aligned_data_csv from summary."""
        return self.summary.aligned_data_csv

    @property
    def column_mappings(self) -> dict[str, str]:
        """Backward compatibility: derive column mappings from change details."""
        mappings = {}
        for change in self.schema_alignment_results:
            if change.change_type == "rename" and change.original_column and change.new_column:
                mappings[change.original_column] = change.new_column
        return mappings

    @property
    def transformation_summary(self) -> dict[str, any]:
        """Backward compatibility: create transformation summary from summary data."""
        return {
            "columns_renamed": self.summary.columns_renamed,
            "columns_added": self.summary.columns_added,
            "columns_removed": self.summary.columns_removed,
            "rows_original": self.summary.rows_original,
            "rows_aligned": self.summary.rows_aligned,
            "total_transformations": self.summary.total_changes,
            "transformation_type": "snake_case_to_camel_case",
        }

    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary for storage."""
        summary_dict = self.summary.model_dump()
        # Ensure timestamp is converted to ISO format string
        if isinstance(summary_dict.get("timestamp"), datetime):
            summary_dict["timestamp"] = summary_dict["timestamp"].isoformat()

        return {
            "schema_alignment_results": [change.model_dump() for change in self.schema_alignment_results],
            "summary": summary_dict,
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> "SchemaAlignmentResults":
        """Create from dictionary loaded from storage."""
        schema_alignment_results = [
            SchemaAlignmentChangeDetail(**change) for change in data.get("schema_alignment_results", [])
        ]
        summary_data = data["summary"]
        if "timestamp" in summary_data and isinstance(summary_data["timestamp"], str):
            summary_data["timestamp"] = datetime.fromisoformat(summary_data["timestamp"])
        summary = SchemaAlignmentResultsSummary(**summary_data)

        return cls(schema_alignment_results=schema_alignment_results, summary=summary)
