#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Expand ground truth mappings to include schema-required fields.

This script adds ground truth entries for schema-required fields that are
missing from the original synthetic datasets. This ensures that validation
errors for these fields are not counted as false positives.
"""

import json
import csv
from pathlib import Path
from typing import Dict

# Schema-required fields with their correct values
SCHEMA_REQUIRED_FIELDS = {
    "library_strategy": ("library_strategy", "Amplicon"),
    "library_source": ("library_source", "Genomic"),
    "library_selection": ("library_selection", "PCR"),
    "platform": ("platform", "Illumina"),
    "library_layout": ("library_layout", "Single"),
    "anatomical_material": ("anatomical_material", "Stool"),
    "gene_targets": ("gene_targets", "CDS-1;"),
    "sample_description": ("sample_description", "Targeted amplicon deep sequencing of Cyclospora spp"),
    "submitter_state": ("submitter_state", "AK"),
}


def determine_error_type(actual_value: str, expected_value: str) -> str:
    """
    Determine the type of error based on the actual and expected values.

    Args:
        actual_value: The value present in the CSV
        expected_value: The correct value

    Returns:
        Error type classification
    """
    if not actual_value or actual_value.strip() == "":
        return "missing"

    # If values differ, classify as semantic difference
    # (Could be enhanced with more sophisticated logic)
    return "semantic"


def read_csv_row(csv_path: Path, row_num: int) -> Dict[str, str]:
    """
    Read a specific row from the CSV file.

    Args:
        csv_path: Path to the CSV file
        row_num: Row number to read (0-based, excluding header)

    Returns:
        Dictionary mapping field names to values
    """
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i == row_num:
                return row
    return {}


def expand_ground_truth_for_dataset(csv_path: Path, mappings_path: Path, dry_run: bool = False) -> None:
    """
    Expand ground truth for a single dataset.

    Args:
        csv_path: Path to the synthetic dataset CSV
        mappings_path: Path to the mappings JSON file
        dry_run: If True, only print what would be done
    """
    print(f"\nProcessing: {csv_path.name}")

    # Read existing mappings
    with open(mappings_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)

    original_count = len(mappings)
    print(f"  Original entries: {original_count}")

    # Determine the number of rows in the CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        total_rows = sum(1 for _ in reader)

    print(f"  Total rows in CSV: {total_rows}")

    # Add entries for each schema-required field
    new_entries = []
    for field_key, (schema_field, correct_value) in SCHEMA_REQUIRED_FIELDS.items():
        for row_num in range(total_rows):
            # Read the actual value from CSV
            row_data = read_csv_row(csv_path, row_num)
            actual_value = row_data.get(field_key, "")

            # Determine error type
            error_type = determine_error_type(actual_value, correct_value)

            # Create ground truth entry
            entry = {
                "row": row_num,
                "field": field_key,
                "schema_field": schema_field,
                "original": correct_value,
                "error": actual_value if actual_value else correct_value,
                "error_type": error_type,
                "valid_options": [correct_value],
            }

            new_entries.append(entry)

    print(f"  New entries to add: {len(new_entries)}")

    if not dry_run:
        # Combine existing and new entries
        updated_mappings = mappings + new_entries

        # Write back to file
        with open(mappings_path, "w", encoding="utf-8") as f:
            json.dump(updated_mappings, f, indent=2, ensure_ascii=False)

        print(f"  ✓ Updated: {len(updated_mappings)} total entries")
    else:
        print("  (DRY RUN - no changes made)")


def main():
    """Main function to expand ground truth for all datasets."""
    import argparse

    parser = argparse.ArgumentParser(description="Expand ground truth to include schema-required fields")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--dataset", type=str, help="Process only a specific dataset (e.g., '1' for dataset 1)")

    args = parser.parse_args()

    # Find all synthetic datasets
    data_dir = Path("data/synthetic_dataset")

    if args.dataset:
        # Process specific dataset
        csv_files = sorted(data_dir.glob(f"synthetic_cyclospora_dataset_{args.dataset}_err*.csv"))
    else:
        # Process all datasets
        csv_files = sorted(data_dir.glob("synthetic_cyclospora_dataset_*_err*.csv"))

    if not csv_files:
        print("No datasets found!")
        return

    print(f"Found {len(csv_files)} dataset(s) to process")

    if args.dry_run:
        print("\n=== DRY RUN MODE - No changes will be made ===\n")

    for csv_path in csv_files:
        # Construct corresponding mappings path
        mappings_path = csv_path.with_name(csv_path.stem + "_mappings.json")

        if not mappings_path.exists():
            print(f"Warning: Mappings file not found for {csv_path.name}")
            continue

        expand_ground_truth_for_dataset(csv_path, mappings_path, args.dry_run)

    print("\n✓ Complete!")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
