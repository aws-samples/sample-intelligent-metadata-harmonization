# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Change detection utility for metadata harmonization processing.

This utility implements the core functionality for detecting changes between
different versions of processing results, creating detailed change objects
that capture modifications, additions, and removals.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional

from loguru import logger

from ..interfaces.result_saver import ResultSaver
from ..models.change_tracking import ChangeObject
from ..models.combined_results import CombinedResults
from ..models.schema_alignment_results import SchemaAlignmentResults
from ..models.validation import (
    ValidationErrorDetail,
    ValidationResults,
)

if TYPE_CHECKING:
    import pandas as pd


class ChangeDetector:
    """
    Utility class responsible for detecting and analyzing changes between result versions.

    This utility provides the core functionality for comparing different versions
    of processing results and generating detailed change objects that capture
    the type, source, and details of each modification.
    """

    def __init__(self, intelligent_detection: bool = True):
        """Initialize the change detector.

        Args:
            intelligent_detection: If True, uses intelligent column mapping to detect
                schema transformations and avoid false validation changes. If False,
                uses simple cell-by-cell comparison. Default: True.
        """
        self.intelligent_detection = intelligent_detection
        logger.info(f"ChangeDetector initialized with intelligent_detection={intelligent_detection}")

    async def detect_changes(
        self,
        job_id: str,
        current_version: int,
        current_results: CombinedResults,
        result_saver: ResultSaver,
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
        logger.info(f"Starting change detection for job {job_id}, version {current_version}")

        try:
            # Load previous versions
            previous_versions = await self._load_previous_versions(job_id, current_version, result_saver)

            if not previous_versions:
                logger.info(f"No previous versions found for job {job_id}, skipping change detection")
                return []

            # Get the most recent previous version for comparison
            previous_version_num = max(previous_versions.keys())
            previous_results = previous_versions[previous_version_num]

            logger.info(f"Comparing version {current_version} with version {previous_version_num}")

            # Detect both schema and validation changes
            changes = []

            # Always detect schema alignment changes if available
            if current_results.has_schema_alignment_results() and previous_results.has_schema_alignment_results():
                logger.info("Detecting schema alignment changes")
                schema_changes = await self.compare_schema_alignment_changes(
                    previous_results.schema_alignment_results,
                    current_results.schema_alignment_results,
                    previous_version_num,
                    current_version,
                )
                changes.extend(schema_changes)
                logger.info(f"Found {len(schema_changes)} schema alignment changes")

            # Always detect validation changes if available
            if current_results.has_validation_results() and previous_results.has_validation_results():
                logger.info("Detecting validation changes")
                validation_changes = await self.compare_validation_changes(
                    previous_results.validation_results,
                    current_results.validation_results,
                    previous_version_num,
                    current_version,
                    previous_results,
                    current_results,
                )
                changes.extend(validation_changes)
                logger.info(f"Found {len(validation_changes)} validation changes")

            logger.info(f"Detected {len(changes)} total changes for job {job_id}")
            return changes

        except Exception as e:
            logger.error(f"Change detection failed for job {job_id}: {e}")
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
        logger.debug(f"Loading previous versions for job {job_id}")

        try:
            # Get list of all results for this job
            all_job_results = await result_saver.list_results(job_id)

            if not all_job_results:
                logger.debug(f"No previous results found for job {job_id}")
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
                            logger.debug(f"Loaded version {version} for job {job_id}")
                        else:
                            logger.warning(f"Could not load results for version {version}")
                    except Exception as e:
                        logger.warning(f"Failed to load version {version} for job {job_id}: {e}")
                        # Continue with other versions - don't fail entire detection
                        continue

            logger.info(f"Loaded {len(previous_versions)} previous versions for job {job_id}")
            return previous_versions

        except Exception as e:
            logger.error(f"Failed to load previous versions for job {job_id}: {e}")
            raise

    async def compare_schema_alignment_changes(
        self,
        previous: SchemaAlignmentResults,
        current: SchemaAlignmentResults,
        source_version: int,
        target_version: int,
    ) -> List[ChangeObject]:
        """
        Compare schema alignment results to detect structural changes.

        This method detects column-level changes like additions, removals, and renames
        that occur during schema alignment processing.

        Args:
            previous: Previous SchemaAlignmentResults instance
            current: Current SchemaAlignmentResults instance
            source_version: Version number of the previous results
            target_version: Version number of the current results

        Returns:
            List of ChangeObject instances for schema alignment changes
        """
        logger.debug(f"Comparing schema alignment changes between versions {source_version} and {target_version}")

        changes = []
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            # Parse CSV data from both versions to detect column changes
            from io import StringIO

            import pandas as pd

            previous_df = pd.read_csv(StringIO(previous.summary.original_data_csv))
            current_df = pd.read_csv(StringIO(current.summary.original_data_csv))

            # Detect column changes
            prev_columns = set(previous_df.columns)
            curr_columns = set(current_df.columns)

            # Column additions
            for col in curr_columns - prev_columns:
                change = ChangeObject(
                    change_type="add",
                    source_type="system",  # Schema alignment is system-driven
                    component="schema_alignment",
                    row=None,  # Schema-level changes don't have specific row
                    column=col,
                    old_value=None,
                    new_value="column_added",
                    timestamp=timestamp,
                    source_version=source_version,
                    target_version=target_version,
                )
                changes.append(change)

            # Column removals
            for col in prev_columns - curr_columns:
                change = ChangeObject(
                    change_type="remove",
                    source_type="system",  # Schema alignment is system-driven
                    component="schema_alignment",
                    row=None,  # Schema-level changes don't have specific row
                    column=col,
                    old_value="column_existed",
                    new_value=None,
                    timestamp=timestamp,
                    source_version=source_version,
                    target_version=target_version,
                )
                changes.append(change)

            # Column renames (if intelligent detection is enabled)
            if self.intelligent_detection:
                column_mappings = self._detect_column_mappings(previous_df, current_df)
                for old_col, new_col in column_mappings.items():
                    change = ChangeObject(
                        change_type="rename",
                        source_type="system",  # Schema alignment is system-driven
                        component="schema_alignment",
                        row=None,  # Schema-level changes don't have specific row
                        column=old_col,
                        old_value=old_col,
                        new_value=new_col,
                        timestamp=timestamp,
                        source_version=source_version,
                        target_version=target_version,
                    )
                    changes.append(change)

        except Exception as e:
            logger.error(f"Failed to compare schema alignment changes: {e}")
            # Continue without schema alignment comparison

        logger.debug(f"Found {len(changes)} schema alignment changes")
        return changes

    async def compare_validation_changes(
        self,
        previous: ValidationResults,
        current: ValidationResults,
        source_version: int,
        target_version: int,
        previous_results: Optional["CombinedResults"] = None,
        current_results: Optional["CombinedResults"] = None,
    ) -> List[ChangeObject]:
        """
        Compare validation results to detect actual CSV cell value changes.

        This method compares the CSV data from schema alignment results to identify
        cell-level changes between versions, using intelligent detection if enabled
        to avoid false positives from column transformations.

        Args:
            previous: Previous ValidationResults instance
            current: Current ValidationResults instance
            source_version: Version number of the previous results
            target_version: Version number of the current results
            previous_results: Previous CombinedResults for CSV data access
            current_results: Current CombinedResults for CSV data access

        Returns:
            List of ChangeObject instances for CSV cell value changes
        """
        logger.debug(f"Comparing validation changes between versions {source_version} and {target_version}")

        changes = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # Try to compare actual CSV data if available in schema alignment results
        if (
            previous_results
            and previous_results.has_schema_alignment_results()
            and current_results
            and current_results.has_schema_alignment_results()
        ):
            try:
                csv_changes = await self._compare_csv_cell_values(
                    previous_results.schema_alignment_results,
                    current_results.schema_alignment_results,
                    source_version,
                    target_version,
                    timestamp,
                    previous_results,
                    current_results,
                )
                changes.extend(csv_changes)
            except Exception as e:
                logger.warning(f"Failed to compare CSV data, falling back to validation errors: {e}")
                # Fallback to validation error comparison
                changes.extend(
                    self._compare_validation_errors(
                        previous.validation_results,
                        current.validation_results,
                        source_version,
                        target_version,
                        timestamp,
                    )
                )
        else:
            # Fallback to validation error comparison
            changes.extend(
                self._compare_validation_errors(
                    previous.validation_results,
                    current.validation_results,
                    source_version,
                    target_version,
                    timestamp,
                )
            )

        logger.debug(f"Found {len(changes)} validation changes")
        return changes

    async def _compare_csv_cell_values(
        self,
        previous: SchemaAlignmentResults,
        current: SchemaAlignmentResults,
        source_version: int,
        target_version: int,
        timestamp: str,
        previous_results: Optional["CombinedResults"] = None,
        current_results: Optional["CombinedResults"] = None,
    ) -> List[ChangeObject]:
        """
        Compare CSV cell values between schema alignment results.

        This method compares actual CSV data to detect cell-level changes,
        using intelligent detection to avoid false positives from column transformations.

        Args:
            previous: Previous SchemaAlignmentResults instance
            current: Current SchemaAlignmentResults instance
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the changes
            previous_results: Previous CombinedResults for recommendation lookup
            current_results: Current CombinedResults for recommendation lookup

        Returns:
            List of ChangeObject instances for cell-level changes
        """
        logger.debug(f"Comparing CSV cell values between versions {source_version} and {target_version}")

        changes = []

        try:
            # Parse CSV data from both versions
            from io import StringIO

            import pandas as pd

            previous_df = pd.read_csv(StringIO(previous.summary.original_data_csv))
            current_df = pd.read_csv(StringIO(current.summary.original_data_csv))

            # If intelligent detection is enabled, get column mappings to avoid false positives
            column_mappings = {}
            if self.intelligent_detection:
                column_mappings = self._detect_column_mappings(previous_df, current_df)
                logger.debug(f"Detected {len(column_mappings)} column mappings")

            # Compare cell values using appropriate logic with column mappings
            changes.extend(
                self._compare_csv_cell_changes_with_mappings(
                    previous_df,
                    current_df,
                    source_version,
                    target_version,
                    timestamp,
                    previous_results,
                    current_results,
                    column_mappings,
                )
            )

        except Exception as e:
            logger.error(f"Failed to compare CSV cell values: {e}")
            raise

        logger.debug(f"Found {len(changes)} CSV cell value changes")
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
                    previous_error,
                    current_error,
                    coordinate,
                    source_version,
                    target_version,
                    timestamp,
                )
                changes.extend(error_changes)

        return changes

    def _detect_column_mappings(self, previous_df: "pd.DataFrame", current_df: "pd.DataFrame") -> Dict[str, str]:
        """
        Detect column mappings between two DataFrames to identify renames.

        This method uses content similarity to detect when columns have been renamed
        but contain similar data.

        Args:
            previous_df: Previous version DataFrame
            current_df: Current version DataFrame

        Returns:
            Dictionary mapping old column names to new column names
        """
        mappings = {}

        prev_columns = set(previous_df.columns)
        curr_columns = set(current_df.columns)

        # Find columns that exist only in previous (potential old names)
        old_only_columns = prev_columns - curr_columns

        # Find columns that exist only in current (potential new names)
        new_only_columns = curr_columns - prev_columns

        if not old_only_columns or not new_only_columns:
            return mappings

        # Compare content similarity between old and new columns
        for old_col in old_only_columns:
            best_match = None
            best_similarity = 0.0

            for new_col in new_only_columns:
                similarity = self._calculate_column_similarity(previous_df[old_col], current_df[new_col])

                if similarity > best_similarity and similarity > 0.8:  # 80% similarity threshold
                    best_similarity = similarity
                    best_match = new_col

            if best_match:
                mappings[old_col] = best_match
                logger.debug(f"Detected column mapping: {old_col} -> {best_match} (similarity: {best_similarity:.2f})")

        return mappings

    def _calculate_column_similarity(self, series1: "pd.Series", series2: "pd.Series") -> float:
        """
        Calculate similarity between two pandas Series.

        Args:
            series1: First series to compare
            series2: Second series to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            import pandas as pd

            # Handle different lengths by taking minimum
            min_len = min(len(series1), len(series2))
            if min_len == 0:
                return 0.0

            s1 = series1.iloc[:min_len]
            s2 = series2.iloc[:min_len]

            # Convert to strings and compare
            s1_str = s1.astype(str).str.strip()
            s2_str = s2.astype(str).str.strip()

            # Calculate exact matches
            matches = (s1_str == s2_str).sum()

            # Handle NaN values - both NaN should count as match
            both_nan = (pd.isna(s1) & pd.isna(s2)).sum()

            total_matches = matches + both_nan
            similarity = total_matches / min_len

            return similarity

        except Exception as e:
            logger.warning(f"Error calculating column similarity: {e}")
            return 0.0

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
            if new_error.confidence_score > 0.5:
                source_type = "system"
                confidence_score = new_error.confidence_score
            else:
                source_type = "user"
                # Don't set confidence_score for user changes
        elif old_error and old_error.recommended_value:
            if old_error.confidence_score > 0.5:
                source_type = "system"
                confidence_score = old_error.confidence_score
            else:
                source_type = "user"
                # Don't set confidence_score for user changes

        # Create old and new values for the change
        old_value = None
        new_value = None

        if old_error:
            old_value = {
                "current_value": old_error.current_value,
                "error_type": old_error.error_type.value,
                "recommended_value": old_error.recommended_value,
                "confidence_score": old_error.confidence_score,
            }

        if new_error:
            new_value = {
                "current_value": new_error.current_value,
                "error_type": new_error.error_type.value,
                "recommended_value": new_error.recommended_value,
                "confidence_score": new_error.confidence_score,
            }

        # Parse row and column from coordinate string (format: "row:column")
        row_str, column_str = coordinate.split(":")
        row = int(row_str)

        return ChangeObject(
            change_type=change_type,
            source_type=source_type,
            component="validation",
            row=row,
            column=column_str,
            old_value=old_value,
            new_value=new_value,
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

        # Parse row and column from coordinate string for all error details
        row_str, column_str = coordinate.split(":")
        row = int(row_str)

        # Compare current values
        if previous_error.current_value != current_error.current_value:
            change = ChangeObject(
                change_type="rename",
                source_type="user",  # Value changes are typically user-driven
                component="validation",
                row=row,
                column=column_str,
                old_value=previous_error.current_value,
                new_value=current_error.current_value,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        # Compare recommended values
        if previous_error.recommended_value != current_error.recommended_value:
            # Determine source type based on confidence scores
            source_type = "system"
            if current_error.confidence_score > 0.5:
                source_type = "system"
            elif current_error.confidence_score > 0.0:
                source_type = "user"  # Low confidence might indicate user override

            change = ChangeObject(
                change_type="rename",
                source_type=source_type,
                component="validation",
                row=row,
                column=column_str,
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
                source_type="system",  # Confidence scores are system-generated
                component="validation",
                row=row,
                column=column_str,
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
                source_type="system",  # Error type changes are system-determined
                component="validation",
                row=row,
                column=column_str,
                old_value=previous_error.error_type.value,
                new_value=current_error.error_type.value,
                timestamp=timestamp,
                source_version=source_version,
                target_version=target_version,
            )
            changes.append(change)

        return changes

    def _compare_csv_cell_changes_with_mappings(
        self,
        previous_df: "pd.DataFrame",
        current_df: "pd.DataFrame",
        source_version: int,
        target_version: int,
        timestamp: str,
        previous_results: Optional["CombinedResults"] = None,
        current_results: Optional["CombinedResults"] = None,
        column_mappings: Dict[str, str] = None,
    ) -> List[ChangeObject]:
        """
        Compare individual cell values between CSV versions with intelligent column mapping.

        This method uses column mappings to avoid false positives when columns are renamed
        but values remain the same. It only reports actual value changes, not changes due
        to column transformations.

        Args:
            previous_df: Previous version DataFrame
            current_df: Current version DataFrame
            source_version: Version number of the previous results
            target_version: Version number of the current results
            timestamp: ISO timestamp for the changes
            previous_results: Previous CombinedResults for recommendation lookup
            current_results: Current CombinedResults for recommendation lookup
            column_mappings: Dictionary mapping old column names to new column names

        Returns:
            List of ChangeObject instances for cell-level changes
        """
        changes = []
        column_mappings = column_mappings or {}

        # Create effective column mapping (including mapped and unchanged columns)
        # For intelligent detection, we need to handle column mappings properly
        effective_mappings = column_mappings.copy()

        # Add identity mappings for columns that exist in both versions unchanged
        common_columns = set(previous_df.columns) & set(current_df.columns)
        for col in common_columns:
            if col not in column_mappings and col not in column_mappings.values():
                effective_mappings[col] = col

        min_rows = min(len(previous_df), len(current_df))

        # Compare values using effective column mappings
        for prev_col, curr_col in effective_mappings.items():
            # Skip if either column doesn't exist
            if prev_col not in previous_df.columns or curr_col not in current_df.columns:
                continue

            for row in range(min_rows):
                try:
                    prev_value = previous_df.iloc[row][prev_col]
                    curr_value = current_df.iloc[row][curr_col]

                    # Handle NaN values
                    import pandas as pd

                    prev_is_nan = pd.isna(prev_value)
                    curr_is_nan = pd.isna(curr_value)

                    # Check for changes
                    if prev_is_nan and curr_is_nan:
                        continue  # Both NaN, no change
                    elif prev_is_nan and not curr_is_nan:
                        # Value added - check if there was a system recommendation
                        source_type, confidence_score = self._determine_change_source(
                            row,
                            curr_col,
                            None,
                            str(curr_value),
                            previous_results,
                            current_results,
                        )
                        change = ChangeObject(
                            change_type="add",
                            source_type=source_type,
                            component="validation",
                            row=row + 1,  # Convert 0-based to 1-based row index
                            column=curr_col,  # Use current column name
                            old_value=None,
                            new_value=str(curr_value),
                            timestamp=timestamp,
                            source_version=source_version,
                            target_version=target_version,
                            confidence_score=confidence_score,
                        )
                        changes.append(change)
                    elif not prev_is_nan and curr_is_nan:
                        # Value removed
                        source_type, confidence_score = self._determine_change_source(
                            row,
                            curr_col,
                            str(prev_value),
                            None,
                            previous_results,
                            current_results,
                        )
                        change = ChangeObject(
                            change_type="remove",
                            source_type=source_type,
                            component="validation",
                            row=row + 1,  # Convert 0-based to 1-based row index
                            column=curr_col,  # Use current column name
                            old_value=str(prev_value),
                            new_value=None,
                            timestamp=timestamp,
                            source_version=source_version,
                            target_version=target_version,
                            confidence_score=confidence_score,
                        )
                        changes.append(change)
                    elif str(prev_value) != str(curr_value):
                        # Value changed - check if there was a system recommendation
                        source_type, confidence_score = self._determine_change_source(
                            row,
                            curr_col,
                            str(prev_value),
                            str(curr_value),
                            previous_results,
                            current_results,
                        )
                        change = ChangeObject(
                            change_type="rename",
                            source_type=source_type,
                            component="validation",
                            row=row + 1,  # Convert 0-based to 1-based row index
                            column=curr_col,  # Use current column name
                            old_value=str(prev_value),
                            new_value=str(curr_value),
                            timestamp=timestamp,
                            source_version=source_version,
                            target_version=target_version,
                            confidence_score=confidence_score,
                        )
                        changes.append(change)

                except Exception as e:
                    logger.warning(f"Error comparing cell [{row},{curr_col}]: {e}")
                    continue

        return changes

    def _determine_change_source(
        self,
        row: int,
        col: str,
        old_value: Optional[str],
        new_value: Optional[str],
        previous_results: Optional["CombinedResults"],
        current_results: Optional["CombinedResults"],
    ) -> tuple[str, Optional[float]]:
        """
        Determine if a change was system-recommended or user-initiated.

        Args:
            row: Row index of the change
            col: Column name of the change
            old_value: Previous value
            new_value: New value
            previous_results: Previous CombinedResults for recommendation lookup
            current_results: Current CombinedResults for recommendation lookup

        Returns:
            Tuple of (source_type, confidence_score) where source_type is "system" or "user"
        """
        # Check validation results for recommendations
        if previous_results and previous_results.has_validation_results():
            for error in previous_results.validation_results.validation_results:
                if error.row == row and error.column == col:
                    # Check if the new value matches a system recommendation
                    if (
                        error.recommended_value
                        and new_value
                        and str(error.recommended_value).strip() == str(new_value).strip()
                    ):
                        return "system", error.confidence_score

        # Check schema alignment results for recommendations
        if previous_results and previous_results.has_schema_alignment_results():
            for alignment_change in previous_results.schema_alignment_results.schema_alignment_results:
                # Check if this change matches a schema alignment recommendation
                if alignment_change.new_column == col and alignment_change.confidence_score > 0.5:
                    return "system", alignment_change.confidence_score

        # Default to user-initiated change
        return "user", None

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
