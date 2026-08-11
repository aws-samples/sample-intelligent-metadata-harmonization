# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Schema-aware data loading utilities for metadata harmonization processor.

This module provides utilities to load CSV files with dtypes determined by
the schema definition, preventing unwanted type conversions (e.g., "FALSE" -> False,
or integer strings being converted to floats).
"""

from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from loguru import logger

from ..interfaces.schema_collector import SchemaCollector


async def load_metadata_csv(
    file_path: Union[str, Path],
    program_id: str,
    core_id: str,
    schema_collector: SchemaCollector,
) -> pd.DataFrame:
    """
    Load a CSV file with dtypes determined by the schema definition.

    This function prevents pandas from making incorrect type inferences by
    explicitly setting dtypes based on the schema. This fixes issues like:
    - Boolean strings "FALSE"/"TRUE" being converted to Python bools
    - Integer strings being converted to floats (e.g., "9" -> 9.0)

    Args:
        file_path: Path to the CSV file to load
        program_id: Schema program identifier
        core_id: Schema core identifier
        schema_collector: SchemaCollector implementation to retrieve schema

    Returns:
        DataFrame with dtypes matching the schema definition

    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If schema cannot be loaded or is invalid

    Example:
        >>> from metadata_harmonization_processor.utils.data_loader import load_metadata_csv
        >>> from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
        >>>
        >>> schema_collector = FileBasedSchemaCollector("/path/to/schemas")
        >>> df = await load_metadata_csv(
        ...     "data.csv",
        ...     program_id="influenza_program",
        ...     core_id="influenza_core",
        ...     schema_collector=schema_collector
        ... )
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    logger.info(f"Loading CSV with schema-aware types: {file_path}")
    logger.debug(f"Using schema: program_id={program_id}, core_id={core_id}")

    # Get the combined schema
    schema = await schema_collector.get_schema(program_id, core_id)

    # Build dtype dict from schema properties
    dtype_dict = {}
    properties = schema.get("properties", {})

    for field_name, field_schema in properties.items():
        schema_type = field_schema.get("type", "string")

        # Map JSON Schema type to pandas dtype
        if schema_type == "string":
            dtype_dict[field_name] = str
        elif schema_type == "integer":
            dtype_dict[field_name] = np.int64
        elif schema_type == "number":
            dtype_dict[field_name] = np.float64
        else:
            # Default to string for any unknown type
            logger.debug(f"Unknown schema type '{schema_type}' for field '{field_name}', defaulting to str")
            dtype_dict[field_name] = str

    logger.debug(f"Loading CSV with dtype mapping for {len(dtype_dict)} schema fields")

    # Peek at CSV columns to identify any extra columns not in schema
    # This prevents pandas from doing type inference on unknown columns
    temp_df = pd.read_csv(file_path, nrows=0)
    all_columns = set(temp_df.columns)
    schema_columns = set(dtype_dict.keys())
    extra_columns = all_columns - schema_columns

    if extra_columns:
        logger.info(f"Found {len(extra_columns)} columns not in schema, will load as str: {list(extra_columns)}")
        # Add string dtype for extra columns BEFORE loading the full CSV
        # This prevents pandas from inferring types (e.g., "FALSE" -> False)
        for col in extra_columns:
            dtype_dict[col] = str

    logger.debug(f"Loading CSV with complete dtype mapping for {len(dtype_dict)} total fields")

    # Load CSV with complete dtype mapping (schema fields + extra fields as strings)
    df = pd.read_csv(file_path, dtype=dtype_dict)

    logger.info(f"Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")

    return df
