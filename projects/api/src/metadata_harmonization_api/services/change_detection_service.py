# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Change detection service for metadata harmonization processing.

This service implements the core functionality for detecting changes between
different versions of processing results, creating detailed change objects
that capture modifications, additions, and removals.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone

from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.change_tracking import ChangeObject
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationResultsSummary,
    ValidationErrorDetail,
)
from metadata_harmonization_processor.models.schema_alignment_results import SchemaAlignmentResults
from metadata_harmonization_processor.interfaces.result_saver import ResultSaver

logger = logging.getLogger(__name__)


class ChangeDetectionService:
    """
    Service responsible for detecting and analyzing changes between result versions.

    This service provides the core functionality for comparing different versions
    of processing results and generating detailed change objects that capture
    the type, source, and details of each modification.
    """

    def __init__(self):
        """Initialize the change detection service."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def detect_changes(
        self, job_id: str, current_version: int, current_results: CombinedResults, result_saver: ResultSaver
    ) -> List[ChangeObject]:
        """
        Detect changes between current and previous versions.

        This method loads previous versions of results and compares them with
        the current version to identify all changes that occurred.

        Args:
            job_id: Unique identifier for the processing job
            current_version: Version number of the current results
            current_results: Current CombinedResults instance
            result_saver: ResultSaver instance for loading previous versions

        Returns:
            List of ChangeObject instances representing detected changes

        Raises:
            Exception: If change detection fails due to system errors
        """
        self.logger.info(f"Starting change detection for job {job_id}, version {current_version}")

        try:
            # Load previous versions
            previous_versions = await self._load_previous_versions(job_id, current_version, result_saver)

            if not previous_versions:
                self.logger.info(f"No previous versions found for job {job_id}, skipping change detection")
                return []

            # Get the most recent previous version for comparison
            previous_version_num = max(previous_versions.keys())
            previous_results = previous_versions[previous_version_num]

            self.logger.info(f"Comparing version {current_version} with version {previous_version_num}")

            # Detect changes between versions
            changes = []

            # Compare validation results if both versions have them
            if current_results.has_validation_results() and previous_results.has_validation_results():
                validation_changes = await self.compare_validation_results(
                    previous_results.validation_results,
                    current_results.validation_results,
                    previous_version_num,
                    current_version,
                )
                changes.extend(validation_changes)

            # Compare schema alignment results if both versions have them
            if current_results.has_schema_alignment_results() and previous_results.has_schema_alignment_results():
                schema_changes = await self.compare_schema_alignment_results(
                    previous_results.schema_alignment_results,
                    current_results.schema_alignment_results,
                    previous_version_num,
                    current_version,
                )
                changes.extend(schema_changes)

            self.logger.info(f"Detected {len(changes)} changes for job {job_id}")
            return changes

        except Exception as e:
            self.logger.error(f"Change detection failed for job {job_id}: {e}")
            raise

    async def _load_previous_versions(
        self, job_id: str, current_version: int, result_saver: ResultSaver
    ) -> Dict[int, CombinedResults]:
        """
        Load all previous versions of results for comparison.

        Args:
            job_id: Unique identifier for the processing job
            current_version: Current version number (to exclude from loading)
            result_saver: ResultSaver instance for loading results

        Returns:
            Dictionary mapping version numbers to CombinedResults instances

        Raises:
            Exception: If loading previous versions fails
        """
        self.logger.debug(f"Loading previous versions for job {job_id}")

        try:
            # Get list of all results for this job
            all_job_results = await result_saver.list_results(job_id)

            if not all_job_results:
                self.logger.debug(f"No previous results found for job {job_id}")
                return {}

            # Filter out current version and load previous versions
            previous_versions = {}

            for job_result in all_job_results:
                # Extract version from location path
                version = self._extract_version_from_location(job_result.location)
                if version and version < current_version:
                    try:
                        combined_results = await result_saver.get_results(job_result)
                        if combined_results:
                            previous_versions[version] = combined_results
                            self.logger.debug(f"Loaded version {version} for job {job_id}")
                        else:
                            self.logger.warning(f"Could not load results for version {version}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load version {version} for job {job_id}: {e}")
                        # Continue with other versions - don't fail entire detection
                        continue

            self.logger.info(f"Loaded {len(previous_versions)} previous versions for job {job_id}")
            return previous_versions

        except Exception as e:
            self.logger.error(f"Failed to load previous versions for job {job_id}: {e}")
            raise

    async def compare_validation_results(
        self, previous: ValidationResults, current: ValidationResults, source_version: int, target_version: int
    ) -> List[ChangeObject]:
        """
        Compare validation results and generate change objects.

        This method performs cell-level comparison of validation data to identify
        changes in error states, corrections, and data values.

        Args:
            previous: Previous ValidationResults instance
            current: Current ValidationResults instance
            source_version: Version number of the previous results
            target_version: Version number of the current results

        Returns:
            List of ChangeObject instances for validation changes
        """
        self.logger.debug(f"Comparing validation results between versions {source_version} and {target_version}")

        changes = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # Compare summary-level changes
        changes.extend(
            self._compare_validation_summary(
                previous.summary, current.summary, source_version, target_version, timestamp
            )
        )

        # Compare cell-level validation errors
        changes.extend(
            self._compare_validation_errors(
                previous.validation_results, current.validation_results, source_version, target_version, timestamp
            )
        )

        self.logger.debug(f"Found {len(changes)} validation changes")
        return changes

    def _compare_validation_summary(
        self,
        previous: ValidationResultsSummary,
        current: ValidationResultsSummary,
        source_version: int,
        target_version: int,
        timestamp: str,
    ) -> List[ChangeObject]:
        """
        Compare validation summary statistics and generate change objects.

        Args:
            previous: Previous ValidationResultsSummary instance
            current: Current ValidationResultsSummary instance
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the changes

        Returns:
            List of ChangeObject instances for summary changes
        """
        changes = []

        # Compare total errors
        # Note: Summary-level changes use schema_alignment component since validation requires row
        if previous.total_errors != current.total_errors:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="schema_alignment",
                column="summary.total_errors",
                old_value=previous.total_errors,
                new_value=current.total_errors,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        # Compare total rows
        if previous.total_rows != current.total_rows:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="schema_alignment",
                column="summary.total_rows",
                old_value=previous.total_rows,
                new_value=current.total_rows,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        # Compare error types
        for error_type, current_count in current.error_types.items():
            previous_count = previous.error_types.get(error_type, 0)
            if previous_count != current_count:
                change = ChangeObject(
                    change_type="rename",
                    source_type="system",
                    component="schema_alignment",
                    column=f"summary.error_types.{error_type.value}",
                    old_value=previous_count,
                    new_value=current_count,
                    timestamp=timestamp,
                    source_version=source_version,
                    target_version=target_version,
                )
                changes.append(change)

        # Check for removed error types
        for error_type, previous_count in previous.error_types.items():
            if error_type not in current.error_types and previous_count > 0:
                change = ChangeObject(
                    change_type="remove",
                    source_type="system",
                    component="schema_alignment",
                    column=f"summary.error_types.{error_type.value}",
                    old_value=previous_count,
                    new_value=None,
                    timestamp=timestamp,
                    source_version=source_version,
                    target_version=target_version,
                )
                changes.append(change)

        return changes

    def _compare_validation_errors(
        self,
        previous_errors: List[ValidationErrorDetail],
        current_errors: List[ValidationErrorDetail],
        source_version: int,
        target_version: int,
        timestamp: str,
    ) -> List[ChangeObject]:
        """
        Compare individual validation errors and generate change objects.

        This method performs cell-level comparison by creating a mapping of
        (row, column) coordinates to error details and comparing them.

        Args:
            previous_errors: List of previous ValidationErrorDetail instances
            current_errors: List of current ValidationErrorDetail instances
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the changes

        Returns:
            List of ChangeObject instances for cell-level changes
        """
        changes = []

        # Create mappings for efficient comparison
        previous_map = self._create_error_coordinate_map(previous_errors)
        current_map = self._create_error_coordinate_map(current_errors)

        # Find all unique coordinates
        all_coordinates = set(previous_map.keys()) | set(current_map.keys())

        for coordinate in all_coordinates:
            previous_error = previous_map.get(coordinate)
            current_error = current_map.get(coordinate)

            if previous_error is None and current_error is not None:
                # New error added
                change = self._create_error_change_object(
                    change_type="add",
                    coordinate=coordinate,
                    old_error=None,
                    new_error=current_error,
                    source_version=source_version,
                    target_version=target_version,
                    timestamp=timestamp,
                )
                changes.append(change)

            elif previous_error is not None and current_error is None:
                # Error removed (fixed)
                change = self._create_error_change_object(
                    change_type="remove",
                    coordinate=coordinate,
                    old_error=previous_error,
                    new_error=None,
                    source_version=source_version,
                    target_version=target_version,
                    timestamp=timestamp,
                )
                changes.append(change)

            elif previous_error is not None and current_error is not None:
                # Error modified - check for changes in error details
                error_changes = self._compare_error_details(
                    previous_error, current_error, coordinate, source_version, target_version, timestamp
                )
                changes.extend(error_changes)

        return changes

    def _create_error_coordinate_map(self, errors: List[ValidationErrorDetail]) -> Dict[str, ValidationErrorDetail]:
        """
        Create a mapping from cell coordinates to error details.

        Args:
            errors: List of ValidationErrorDetail instances

        Returns:
            Dictionary mapping coordinate strings to error details
        """
        error_map = {}
        for error in errors:
            coordinate = f"{error.row}:{error.column}"
            error_map[coordinate] = error
        return error_map

    def _create_error_change_object(
        self,
        change_type: str,
        coordinate: str,
        old_error: Optional[ValidationErrorDetail],
        new_error: Optional[ValidationErrorDetail],
        source_version: int,
        target_version: int,
        timestamp: str,
    ) -> ChangeObject:
        """
        Create a ChangeObject for a validation error change.

        Args:
            change_type: Type of change (add, remove, rename)
            coordinate: Cell coordinate string (row:column)
            old_error: Previous error detail (None for add operations)
            new_error: Current error detail (None for remove operations)
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the change

        Returns:
            ChangeObject instance representing the error change
        """
        # Determine source type based on confidence score and recommended value
        source_type = "system"
        confidence_score = None

        if new_error and new_error.recommended_value:
            # If there's a recommended value with high confidence, it's likely system-generated
            if new_error.confidence_score is not None and new_error.confidence_score > 0.5:
                source_type = "system"
                confidence_score = new_error.confidence_score
            else:
                source_type = "user"
                # Don't set confidence_score for user changes
        elif old_error and old_error.recommended_value:
            if old_error.confidence_score is not None and old_error.confidence_score > 0.5:
                source_type = "system"
                confidence_score = old_error.confidence_score
            else:
                source_type = "user"
                # Don't set confidence_score for user changes

        # Parse coordinate into row and column
        row_str, col_name = coordinate.split(":", 1)

        return ChangeObject(
            change_type=change_type,
            source_type=source_type,
            component="validation",
            row=int(row_str),
            column=col_name,
            old_value=old_error.current_value if old_error else None,
            new_value=new_error.current_value if new_error else None,
            timestamp=timestamp,
            source_version=source_version,
            target_version=target_version,
            confidence_score=confidence_score,
        )

    def _compare_error_details(
        self,
        previous_error: ValidationErrorDetail,
        current_error: ValidationErrorDetail,
        coordinate: str,
        source_version: int,
        target_version: int,
        timestamp: str,
    ) -> List[ChangeObject]:
        """
        Compare details of validation errors at the same coordinate.

        Args:
            previous_error: Previous ValidationErrorDetail instance
            current_error: Current ValidationErrorDetail instance
            coordinate: Cell coordinate string (row:column)
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the changes

        Returns:
            List of ChangeObject instances for detailed error changes
        """
        changes = []

        # Parse coordinate into row and column
        row_str, col_name = coordinate.split(":", 1)
        row_num = int(row_str)

        # Compare current values
        if previous_error.current_value != current_error.current_value:
            change = ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=row_num,
                column=col_name,
                old_value=previous_error.current_value,
                new_value=current_error.current_value,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        # Compare recommended values
        if previous_error.recommended_value != current_error.recommended_value:
            source_type = "system"
            if current_error.confidence_score > 0.5:
                source_type = "system"
            elif current_error.confidence_score > 0.0:
                source_type = "user"

            change = ChangeObject(
                change_type="rename",
                source_type=source_type,
                component="validation",
                row=row_num,
                column=col_name,
                old_value=previous_error.recommended_value,
                new_value=current_error.recommended_value,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
                confidence_score=current_error.confidence_score,
            )
            changes.append(change)

        # Compare confidence scores
        if previous_error.confidence_score != current_error.confidence_score:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="validation",
                row=row_num,
                column=col_name,
                old_value=previous_error.confidence_score,
                new_value=current_error.confidence_score,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
                confidence_score=current_error.confidence_score,
            )
            changes.append(change)

        # Compare error types
        if previous_error.error_type != current_error.error_type:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="validation",
                row=row_num,
                column=col_name,
                old_value=previous_error.error_type.value,
                new_value=current_error.error_type.value,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        return changes

    async def compare_schema_alignment_results(
        self,
        previous: SchemaAlignmentResults,
        current: SchemaAlignmentResults,
        source_version: int,
        target_version: int,
    ) -> List[ChangeObject]:
        """
        Compare schema alignment results and generate change objects.

        This method compares schema transformation mappings and alignment data
        to identify changes in schema relationships and transformations.

        Args:
            previous: Previous SchemaAlignmentResults instance
            current: Current SchemaAlignmentResults instance
            source_version: Version number of the previous results
            target_version: Version number of the current results

        Returns:
            List of ChangeObject instances for schema alignment changes
        """
        self.logger.debug(f"Comparing schema alignment results between versions {source_version} and {target_version}")

        changes = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # For now, implement basic comparison logic
        # This is a placeholder implementation that will be expanded in future tasks

        # Compare summary fields
        if previous.summary.total_changes != current.summary.total_changes:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="schema_alignment",
                column="summary.total_changes",
                old_value=previous.summary.total_changes,
                new_value=current.summary.total_changes,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        if previous.summary.columns_renamed != current.summary.columns_renamed:
            change = ChangeObject(
                change_type="rename",
                source_type="system",
                component="schema_alignment",
                column="summary.columns_renamed",
                old_value=previous.summary.columns_renamed,
                new_value=current.summary.columns_renamed,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        self.logger.debug(f"Found {len(changes)} schema alignment changes")
        return changes

    def _extract_version_from_location(self, location: str) -> Optional[int]:
        """
        Extract version number from JobResults location path.

        Args:
            location: Storage location path (e.g., "job_123/v2/results.json")

        Returns:
            Version number if found, None otherwise
        """
        try:
            from pathlib import Path

            path_parts = Path(location).parts

            # Look for version directory pattern (v{number})
            for part in path_parts:
                if part.startswith("v") and part[1:].isdigit():
                    return int(part[1:])

            return None
        except (ValueError, IndexError):
            return None
