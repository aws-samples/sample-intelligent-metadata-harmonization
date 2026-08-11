# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Schema alignment utilities for converting between naming conventions.

This module provides utilities for basic schema alignment, including
converting snake_case column names to camelCase for demonstration purposes.
This is a temporary implementation that will be replaced with the full
unified storage approach.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from metadata_harmonization_processor.models.schema_alignment_results import (
        SchemaAlignmentResults,
    )


def snake_to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case string to camelCase.

    Args:
        snake_str: String in snake_case format (e.g., 'patient_id')

    Returns:
        String in camelCase format (e.g., 'patientId')

    Examples:
        >>> snake_to_camel_case('patient_id')
        'patientId'
        >>> snake_to_camel_case('sample_collection_date')
        'sampleCollectionDate'
        >>> snake_to_camel_case('host_scientific_name')
        'hostScientificName'
    """
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def create_basic_column_mapping(original_columns: list[str]) -> dict[str, str]:
    """
    Create a basic column mapping from snake_case to camelCase.

    This is a simple demonstration of schema alignment that converts
    snake_case column names to camelCase equivalents.

    Args:
        original_columns: List of original column names in snake_case

    Returns:
        Dictionary mapping original names to aligned names

    Example:
        >>> create_basic_column_mapping(['patient_id', 'sample_date', 'lab_result'])
        {'patient_id': 'patientId', 'sample_date': 'sampleDate', 'lab_result': 'labResult'}
    """
    column_mapping = {}

    for col in original_columns:
        # Only convert if column contains underscores (is snake_case)
        if "_" in col:
            camel_case_col = snake_to_camel_case(col)
            column_mapping[col] = camel_case_col
        else:
            # Keep column as-is if it's not snake_case
            column_mapping[col] = col

    return column_mapping


def apply_basic_schema_alignment(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Apply basic schema alignment by converting snake_case columns to camelCase.

    This is a temporary implementation for testing purposes that demonstrates
    how schema alignment transformations work.

    Args:
        df: Input DataFrame with snake_case column names

    Returns:
        Tuple of (aligned DataFrame, column mappings dictionary)

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'patient_id': [1, 2], 'sample_date': ['2023-01-01', '2023-01-02']})
        >>> aligned_df, mappings = apply_basic_schema_alignment(df)
        >>> list(aligned_df.columns)
        ['patientId', 'sampleDate']
        >>> mappings
        {'patient_id': 'patientId', 'sample_date': 'sampleDate'}
    """
    # Create column mapping
    column_mapping = create_basic_column_mapping(list(df.columns))

    # Apply column renaming
    aligned_df = df.rename(columns=column_mapping)

    return aligned_df, column_mapping


def create_transformation_summary(
    original_df: pd.DataFrame, aligned_df: pd.DataFrame, column_mapping: dict[str, str]
) -> dict[str, any]:
    """
    Create a transformation summary for basic schema alignment.

    Args:
        original_df: Original DataFrame before alignment
        aligned_df: DataFrame after alignment
        column_mapping: Dictionary of column name mappings

    Returns:
        Dictionary containing transformation summary information
    """
    original_cols = set(original_df.columns)
    aligned_cols = set(aligned_df.columns)

    # Count different types of transformations
    columns_renamed = len([col for col in column_mapping if column_mapping[col] != col])
    columns_added = len(aligned_cols - set(column_mapping.values()))
    columns_removed = len(original_cols - set(column_mapping.keys()))

    return {
        "columns_renamed": columns_renamed,
        "columns_added": columns_added,
        "columns_removed": columns_removed,
        "rows_original": len(original_df),
        "rows_aligned": len(aligned_df),
        "column_mappings": column_mapping,
        "added_columns": list(aligned_cols - set(column_mapping.values())),
        "removed_columns": list(original_cols - set(column_mapping.keys())),
        "processing_timestamp": datetime.now(UTC).isoformat(),
        "transformation_type": "snake_case_to_camel_case",
    }


def dataframe_to_csv_string(df: pd.DataFrame) -> str:
    """
    Convert DataFrame to CSV string for storage.

    Args:
        df: DataFrame to convert

    Returns:
        CSV string representation of the DataFrame
    """
    return df.to_csv(index=False, na_rep="", encoding="utf-8")


# Example data for testing
EXAMPLE_SNAKE_CASE_DATA = {
    "patient_id": ["P001", "P002", "P003"],
    "sample_collection_date": ["2023-01-15", "2023-01-16", "2023-01-17"],
    "lab_result_value": [45.2, 38.7, 52.1],
    "host_scientific_name": ["Homo sapiens", "Homo sapiens", "Homo sapiens"],
    "sequencing_instrument": ["Illumina", "PacBio", "Illumina"],
    "sample_origin_country": ["USA", "Canada", "Mexico"],
}


def create_example_schema_alignment_results(job_id: str, version: int = 1) -> SchemaAlignmentResults:
    """
    Create example SchemaAlignmentResults for testing purposes.

    This function demonstrates how schema alignment works by converting
    snake_case column names to camelCase and creating the corresponding
    transformation data.

    Args:
        job_id: Job identifier for the results
        version: Version number for the results

    Returns:
        SchemaAlignmentResults instance with example data
    """
    from ..models.schema_alignment_results import (
        SchemaAlignmentChangeDetail,
        SchemaAlignmentResults,
        SchemaAlignmentResultsSummary,
    )

    # Create original DataFrame with snake_case columns
    original_df = pd.DataFrame(EXAMPLE_SNAKE_CASE_DATA)

    # Apply basic schema alignment (snake_case to camelCase)
    aligned_df, column_mapping = apply_basic_schema_alignment(original_df)

    # Convert DataFrames to CSV strings
    original_csv = dataframe_to_csv_string(original_df)
    aligned_csv = dataframe_to_csv_string(aligned_df)

    # Create transformation summary
    transformation_summary = create_transformation_summary(original_df, aligned_df, column_mapping)

    # Create change details from column mappings
    schema_alignment_results = []
    for original_col, new_col in column_mapping.items():
        if original_col != new_col:  # Only include renamed columns
            change_detail = SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column=original_col,
                new_column=new_col,
                reason="Converting snake_case to camelCase",
                row_count_affected=len(original_df),
                confidence_score=1.0,
                confidence_level="High",
            )
            schema_alignment_results.append(change_detail)

    # Create summary
    summary = SchemaAlignmentResultsSummary(
        job_id=job_id,
        version=version,
        timestamp=datetime.now(UTC),
        original_data_csv=original_csv,
        aligned_data_csv=aligned_csv,
        total_changes=transformation_summary["columns_renamed"]
        + transformation_summary["columns_added"]
        + transformation_summary["columns_removed"],
        columns_renamed=transformation_summary["columns_renamed"],
        columns_added=transformation_summary["columns_added"],
        columns_removed=transformation_summary["columns_removed"],
        rows_original=transformation_summary["rows_original"],
        rows_aligned=transformation_summary["rows_aligned"],
    )

    # Create and return SchemaAlignmentResults
    return SchemaAlignmentResults(schema_alignment_results=schema_alignment_results, summary=summary)
