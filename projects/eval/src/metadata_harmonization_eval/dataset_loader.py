# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Dataset loader module for the evaluation package.

This module provides functionality to load test datasets (CSV files) and their
corresponding ground truth mappings (JSON files), as well as discover and pair
datasets in a directory.
"""

import json
import re
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger

from .models import DatasetPair, GroundTruth, GroundTruthEntry


class DatasetLoadError(Exception):
    """Exception raised when dataset loading fails."""

    pass


class GroundTruthLoadError(Exception):
    """Exception raised when ground truth loading fails."""

    pass


class DatasetLoader:
    """
    Loader for test datasets and ground truth mappings.

    This class provides static methods to load CSV datasets, ground truth JSON files,
    discover dataset pairs in directories, and validate dataset/ground truth compatibility.
    """

    @staticmethod
    def load_dataset(csv_path: Path) -> pd.DataFrame:
        """
        Load a CSV dataset into a pandas DataFrame.

        This method reads a CSV file and performs basic validation to ensure
        it can be processed. It handles various encoding issues and parsing errors
        gracefully.

        Args:
            csv_path: Path to the CSV file to load

        Returns:
            pandas DataFrame containing the dataset

        Raises:
            DatasetLoadError: If the file cannot be loaded or is invalid

        Example:
            >>> loader = DatasetLoader()
            >>> df = loader.load_dataset(Path("data/test_dataset.csv"))
            >>> print(f"Loaded {len(df)} records")
        """
        if not csv_path.exists():
            raise DatasetLoadError(f"CSV file not found: {csv_path}")

        if not csv_path.is_file():
            raise DatasetLoadError(f"Path is not a file: {csv_path}")

        if csv_path.suffix.lower() != ".csv":
            raise DatasetLoadError(f"File is not a CSV: {csv_path}")

        try:
            # Try reading with UTF-8 encoding first
            df = pd.read_csv(csv_path, encoding="utf-8")
        except UnicodeDecodeError:
            # Fall back to latin-1 encoding if UTF-8 fails
            logger.warning(f"UTF-8 decoding failed for {csv_path}, trying latin-1")
            try:
                df = pd.read_csv(csv_path, encoding="latin-1")
            except Exception as e:
                raise DatasetLoadError(f"Failed to read CSV with multiple encodings: {e}")
        except pd.errors.EmptyDataError:
            raise DatasetLoadError(f"CSV file is empty: {csv_path}")
        except pd.errors.ParserError as e:
            raise DatasetLoadError(f"Failed to parse CSV file: {e}")
        except Exception as e:
            raise DatasetLoadError(f"Unexpected error loading CSV: {e}")

        # Validate that the DataFrame is not empty
        if df.empty:
            raise DatasetLoadError(f"CSV file contains no data: {csv_path}")

        # Validate that there are columns
        if len(df.columns) == 0:
            raise DatasetLoadError(f"CSV file contains no columns: {csv_path}")

        logger.info(f"Loaded dataset from {csv_path.name}: " f"{len(df)} rows, {len(df.columns)} columns")

        return df

    @staticmethod
    def load_ground_truth(json_path: Path) -> GroundTruth:
        """
        Load ground truth mappings from a JSON file.

        This method reads a JSON file containing error mappings and validates
        that it matches the expected schema. It automatically calculates the
        error rate and total error count from the entries.

        Args:
            json_path: Path to the ground truth JSON file

        Returns:
            GroundTruth object containing all error entries and metadata

        Raises:
            GroundTruthLoadError: If the file cannot be loaded or is invalid

        Example:
            >>> loader = DatasetLoader()
            >>> gt = loader.load_ground_truth(Path("data/test_mappings.json"))
            >>> print(f"Loaded {gt.total_errors} errors at {gt.error_rate:.1%} rate")
        """
        if not json_path.exists():
            raise GroundTruthLoadError(f"Ground truth file not found: {json_path}")

        if not json_path.is_file():
            raise GroundTruthLoadError(f"Path is not a file: {json_path}")

        if json_path.suffix.lower() != ".json":
            raise GroundTruthLoadError(f"File is not a JSON: {json_path}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise GroundTruthLoadError(f"Invalid JSON in file: {e}")
        except UnicodeDecodeError as e:
            raise GroundTruthLoadError(f"Encoding error reading file: {e}")
        except Exception as e:
            raise GroundTruthLoadError(f"Unexpected error loading JSON: {e}")

        # Validate that data is a list
        if not isinstance(data, list):
            raise GroundTruthLoadError(f"Ground truth JSON must be a list, got {type(data).__name__}")

        if len(data) == 0:
            raise GroundTruthLoadError("Ground truth JSON contains no entries")

        # Parse entries into GroundTruthEntry objects
        try:
            entries = [GroundTruthEntry(**entry) for entry in data]
        except Exception as e:
            raise GroundTruthLoadError(f"Failed to parse ground truth entries: {e}")

        # Calculate total errors (number of entries)
        total_errors = len(entries)

        # Calculate error rate from filename if available
        # Pattern: synthetic_cyclospora_dataset_1_err40_mappings.json -> 0.40
        error_rate = 0.0
        filename = json_path.stem  # Get filename without extension

        # Try to extract error rate from filename
        match = re.search(r"err(\d+)", filename, re.IGNORECASE)
        if match:
            error_rate_percent = int(match.group(1))
            error_rate = error_rate_percent / 100.0
            logger.debug(f"Extracted error rate {error_rate:.2%} from filename: {filename}")
        else:
            # If we can't extract from filename, we'll need to calculate it
            # This would require knowing the total number of records in the dataset
            # For now, we'll log a warning and use 0.0
            logger.warning(
                f"Could not extract error rate from filename: {filename}. "
                "Error rate will need to be set manually or calculated."
            )

        # Create and return GroundTruth object
        ground_truth = GroundTruth(entries=entries, error_rate=error_rate, total_errors=total_errors)

        logger.info(f"Loaded ground truth from {json_path.name}: " f"{total_errors} errors at {error_rate:.1%} rate")

        return ground_truth

    @staticmethod
    def discover_datasets(directory: Path) -> List[DatasetPair]:
        """
        Discover and pair CSV datasets with their ground truth JSON files.

        This method scans a directory for CSV files and attempts to find their
        corresponding ground truth JSON files. It extracts error rates from
        filenames and creates DatasetPair objects for each valid pair.

        The expected naming convention is:
        - CSV: {name}.csv
        - JSON: {name}_mappings.json

        For example:
        - synthetic_cyclospora_dataset_1_err40.csv
        - synthetic_cyclospora_dataset_1_err40_mappings.json

        Args:
            directory: Path to directory containing dataset files

        Returns:
            List of DatasetPair objects for all discovered pairs

        Raises:
            DatasetLoadError: If the directory doesn't exist or is not accessible

        Example:
            >>> loader = DatasetLoader()
            >>> pairs = loader.discover_datasets(Path("data/synthetic_dataset"))
            >>> print(f"Found {len(pairs)} dataset pairs")
            >>> for pair in pairs:
            ...     print(f"  {pair.dataset_name}: {pair.error_rate:.1%} error rate")
        """
        if not directory.exists():
            raise DatasetLoadError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise DatasetLoadError(f"Path is not a directory: {directory}")

        # Find all CSV files in the directory
        csv_files = list(directory.glob("*.csv"))

        if not csv_files:
            logger.warning(f"No CSV files found in directory: {directory}")
            return []

        logger.info(f"Found {len(csv_files)} CSV files in {directory}")

        dataset_pairs = []

        for csv_path in csv_files:
            # Skip files that end with _mappings.csv (if any exist)
            if csv_path.stem.endswith("_mappings"):
                continue

            # Look for corresponding ground truth JSON file
            # Expected pattern: {csv_stem}_mappings.json
            json_path = directory / f"{csv_path.stem}_mappings.json"

            if not json_path.exists():
                logger.warning(f"No ground truth file found for {csv_path.name}, " f"expected: {json_path.name}")
                continue

            # Extract error rate from filename
            # Pattern: synthetic_cyclospora_dataset_1_err40.csv -> 0.40
            error_rate = 0.0
            match = re.search(r"err(\d+)", csv_path.stem, re.IGNORECASE)
            if match:
                error_rate_percent = int(match.group(1))
                error_rate = error_rate_percent / 100.0
            else:
                logger.warning(f"Could not extract error rate from filename: {csv_path.name}")

            # Create dataset name from filename (without extension)
            dataset_name = csv_path.stem

            # Create DatasetPair
            try:
                pair = DatasetPair(
                    csv_path=csv_path, ground_truth_path=json_path, dataset_name=dataset_name, error_rate=error_rate
                )
                dataset_pairs.append(pair)
                logger.debug(f"Paired dataset: {dataset_name} " f"(error rate: {error_rate:.1%})")
            except Exception as e:
                logger.error(f"Failed to create DatasetPair for {csv_path.name}: {e}")
                continue

        logger.info(f"Successfully paired {len(dataset_pairs)} datasets in {directory}")

        # Sort by error rate for consistent ordering
        dataset_pairs.sort(key=lambda p: (p.error_rate, p.dataset_name))

        return dataset_pairs

    @staticmethod
    def validate_dataset_pair(csv_path: Path, json_path: Path) -> bool:
        """
        Validate that a CSV dataset and ground truth JSON file are compatible.

        This method performs basic validation to ensure that:
        1. Both files exist and are readable
        2. The CSV can be loaded as a DataFrame
        3. The JSON can be parsed as ground truth
        4. The ground truth references valid rows in the dataset

        Args:
            csv_path: Path to the CSV dataset file
            json_path: Path to the ground truth JSON file

        Returns:
            True if the pair is valid and compatible, False otherwise

        Example:
            >>> loader = DatasetLoader()
            >>> is_valid = loader.validate_dataset_pair(
            ...     Path("data/test.csv"),
            ...     Path("data/test_mappings.json")
            ... )
            >>> if is_valid:
            ...     print("Dataset pair is valid")
        """
        try:
            # Try to load the CSV
            df = DatasetLoader.load_dataset(csv_path)
            num_rows = len(df)

            # Try to load the ground truth
            ground_truth = DatasetLoader.load_ground_truth(json_path)

            # Validate that all ground truth row references are within bounds
            invalid_rows = []
            for entry in ground_truth.entries:
                if entry.row < 0 or entry.row >= num_rows:
                    invalid_rows.append(entry.row)

            if invalid_rows:
                logger.error(
                    f"Ground truth contains invalid row references: {invalid_rows}. "
                    f"Dataset has {num_rows} rows (0-{num_rows-1})"
                )
                return False

            # Validate that ground truth fields exist in the dataset
            dataset_columns = set(df.columns)
            missing_fields = set()

            for entry in ground_truth.entries:
                if entry.field not in dataset_columns:
                    missing_fields.add(entry.field)

            if missing_fields:
                logger.warning(
                    f"Ground truth references fields not in dataset: {missing_fields}. "
                    f"Dataset columns: {list(dataset_columns)}"
                )
                # This is a warning, not an error, as field names might be transformed

            logger.info(f"Dataset pair validation passed: {csv_path.name} + {json_path.name}")
            return True

        except (DatasetLoadError, GroundTruthLoadError) as e:
            logger.error(f"Dataset pair validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False
