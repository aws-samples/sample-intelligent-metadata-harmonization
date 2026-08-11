#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Basic Schema Alignment Demonstration

This script demonstrates the basic schema alignment functionality that converts
snake_case column names to camelCase. This is a temporary implementation for
testing purposes that will be replaced with the full unified storage approach.

Example usage:
    python examples/basic_schema_alignment_demo.py
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metadata_harmonization_processor.utils.schema_alignment_utils import (  # noqa: E402
    create_example_schema_alignment_results,
    apply_basic_schema_alignment,
    EXAMPLE_SNAKE_CASE_DATA,
)


def main():
    """Demonstrate basic schema alignment functionality."""
    print("=" * 80)
    print("Basic Schema Alignment Demonstration")
    print("=" * 80)
    print()

    # Create example data with snake_case columns
    print("1. Original Data (snake_case columns):")
    print("-" * 40)
    original_df = pd.DataFrame(EXAMPLE_SNAKE_CASE_DATA)
    print(original_df.to_string(index=False))
    print()
    print(f"Original columns: {list(original_df.columns)}")
    print()

    # Apply basic schema alignment
    print("2. Schema Alignment Process:")
    print("-" * 40)
    aligned_df, column_mappings = apply_basic_schema_alignment(original_df)

    print("Column mappings applied:")
    for original, aligned in column_mappings.items():
        if original != aligned:
            print(f"  {original} → {aligned}")
    print()

    # Show aligned data
    print("3. Aligned Data (camelCase columns):")
    print("-" * 40)
    print(aligned_df.to_string(index=False))
    print()
    print(f"Aligned columns: {list(aligned_df.columns)}")
    print()

    # Create SchemaAlignmentResults
    print("4. SchemaAlignmentResults Creation:")
    print("-" * 40)
    job_id = f"demo-job-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    results = create_example_schema_alignment_results(job_id)

    print(f"Job ID: {results.job_id}")
    print(f"Version: {results.version}")
    print(f"Timestamp: {results.timestamp}")
    print(f"Columns renamed: {results.transformation_summary['columns_renamed']}")
    print(f"Transformation type: {results.transformation_summary['transformation_type']}")
    print()

    # Show CSV data samples
    print("5. CSV Data Samples:")
    print("-" * 40)

    print("Original CSV (first 2 lines):")
    original_lines = results.original_data_csv.strip().split("\n")
    for i, line in enumerate(original_lines[:2]):
        print(f"  {i+1}: {line}")
    print()

    print("Aligned CSV (first 2 lines):")
    aligned_lines = results.aligned_data_csv.strip().split("\n")
    for i, line in enumerate(aligned_lines[:2]):
        print(f"  {i+1}: {line}")
    print()

    # Show transformation summary
    print("6. Transformation Summary:")
    print("-" * 40)
    summary = results.transformation_summary
    print(f"  Columns renamed: {summary['columns_renamed']}")
    print(f"  Columns added: {summary['columns_added']}")
    print(f"  Columns removed: {summary['columns_removed']}")
    print(f"  Original rows: {summary['rows_original']}")
    print(f"  Aligned rows: {summary['rows_aligned']}")
    print()

    # Show serialization
    print("7. Serialization Test:")
    print("-" * 40)
    data_dict = results.to_dict()
    print(f"Serialized to dictionary with {len(data_dict)} keys:")
    for key in data_dict.keys():
        print(f"  - {key}")
    print()

    # Test deserialization
    restored_results = results.__class__.from_dict(data_dict)
    print(f"Successfully deserialized: {restored_results.job_id == results.job_id}")
    print()

    print("=" * 80)
    print("Demonstration Complete!")
    print()
    print("This basic schema alignment shows how:")
    print("• snake_case columns are converted to camelCase")
    print("• Original and aligned data are preserved as CSV strings")
    print("• Column mappings track the transformations")
    print("• Transformation summaries provide metadata")
    print("• Results can be serialized/deserialized for storage")
    print()
    print("This temporary implementation will be replaced with the full")
    print("unified storage approach in the complete solution.")
    print("=" * 80)


if __name__ == "__main__":
    main()
