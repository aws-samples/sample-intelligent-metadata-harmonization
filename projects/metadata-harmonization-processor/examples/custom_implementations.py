#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Custom Implementations Example for MetadataHarmonizationProcessor

This example demonstrates how to create custom implementations
of the JobStatusSaver and SchemaCollector interfaces.
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import pandas as pd

from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.interfaces import JobStatusSaver, SchemaCollector, SchemaInfo


class SQLiteJobStatusSaver(JobStatusSaver):
    """Custom JobStatusSaver implementation using SQLite database."""

    def __init__(self, db_path: str):
        """Initialize with SQLite database path."""
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_status (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_progress (
                    job_id TEXT,
                    stage TEXT,
                    progress REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (job_id, stage),
                    FOREIGN KEY (job_id) REFERENCES job_status (job_id)
                )
            """
            )

    async def save_status(self, job_id: str, status: str, metadata: Dict[str, Any]) -> None:
        """Save job status to SQLite database."""
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_status (job_id, status, metadata, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (job_id, status, metadata_json),
            )

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job status from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT job_id, status, metadata, created_at, updated_at
                FROM job_status WHERE job_id = ?
            """,
                (job_id,),
            )

            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result["metadata"]:
                    result["metadata"] = json.loads(result["metadata"])
                return result

        return None

    async def update_progress(self, job_id: str, stage: str, progress: float) -> None:
        """Update job progress in SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_progress (job_id, stage, progress, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (job_id, stage, progress),
            )


class APISchemaCollector(SchemaCollector):
    """Custom SchemaCollector implementation that fetches schemas from an API."""

    def __init__(self, api_base_url: str, api_key: Optional[str] = None):
        """Initialize with API configuration."""
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._available_schemas_cache: Optional[List[SchemaInfo]] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get_available_schemas(self) -> List[SchemaInfo]:
        """Get available schemas from API."""
        if self._available_schemas_cache is not None:
            return self._available_schemas_cache

        # Simulate API call (replace with actual HTTP request)
        # In real implementation, use aiohttp or similar
        mock_api_response = [
            {
                "core_uuid": "core-001",
                "core_name": "Patient Core Schema",
                "core_path": "schemas/core/patient_v1.json",
                "program_uuid": "prog-001",
                "program_name": "Flu Surveillance Program",
                "program_path": "schemas/programs/flu_v1.json",
            },
            {
                "core_uuid": "core-001",
                "core_name": "Patient Core Schema",
                "core_path": "schemas/core/patient_v1.json",
                "program_uuid": "prog-002",
                "program_name": "COVID Surveillance Program",
                "program_path": "schemas/programs/covid_v1.json",
            },
        ]

        schemas = []
        for item in mock_api_response:
            schemas.append(
                SchemaInfo(
                    core_uuid=item["core_uuid"],
                    core_name=item["core_name"],
                    core_path=item["core_path"],
                    program_uuid=item["program_uuid"],
                    program_name=item["program_name"],
                    program_path=item["program_path"],
                )
            )

        self._available_schemas_cache = schemas
        return schemas

    async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Get combined schema from API."""
        cache_key = f"{program_id}:{core_id}"

        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        # Simulate API calls to get core and program schemas
        # In real implementation, make HTTP requests to:
        # GET {api_base_url}/schemas/core/{core_id}
        # GET {api_base_url}/schemas/program/{program_id}

        mock_core_schema = {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "amd_required": True, "description": "Unique patient identifier"},
                "age": {"type": "integer", "minimum": 0, "maximum": 150, "amd_required": True},
            },
        }

        mock_program_schema = {
            "type": "object",
            "properties": {
                "test_result": {"type": "string", "enum": ["positive", "negative", "pending"], "amd_required": True},
                "test_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "amd_required": False},
            },
        }

        # Combine schemas (program properties override core)
        combined_schema = {
            "type": "object",
            "properties": {**mock_core_schema.get("properties", {}), **mock_program_schema.get("properties", {})},
        }

        self._schema_cache[cache_key] = combined_schema
        return combined_schema

    async def get_schema_columns(self, program_id: str, core_id: str) -> List[str]:
        """Get expected column names from schema."""
        schema = await self.get_schema(program_id, core_id)
        return list(schema.get("properties", {}).keys())

    async def get_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Get validation rules from schema."""
        schema = await self.get_schema(program_id, core_id)
        rules = {}

        for field_name, field_schema in schema.get("properties", {}).items():
            field_rules = {}

            # Required field check
            if field_schema.get("amd_required", False):
                field_rules["required"] = True

            # Enum validation
            if "enum" in field_schema:
                field_rules["valid_options"] = field_schema["enum"]

            # Pattern validation
            if "pattern" in field_schema:
                field_rules["pattern"] = field_schema["pattern"]

            # Type validation
            if "type" in field_schema:
                field_rules["type"] = field_schema["type"]

            # Numeric constraints
            if "minimum" in field_schema:
                field_rules["minimum"] = field_schema["minimum"]
            if "maximum" in field_schema:
                field_rules["maximum"] = field_schema["maximum"]

            if field_rules:
                rules[field_name] = field_rules

        return rules


async def demonstrate_custom_implementations():
    """Demonstrate using custom implementations with the processor."""

    print("=== Custom Implementations Demo ===")

    # Initialize custom implementations
    sqlite_job_saver = SQLiteJobStatusSaver("./examples/job_status.db")
    api_schema_collector = APISchemaCollector(
        api_base_url="https://api.example.com/metadata", api_key="your-api-key-here"
    )

    # Test custom implementations independently
    print("\n1. Testing SQLite JobStatusSaver...")

    # Test job status operations
    await sqlite_job_saver.save_status(
        job_id="test-job-001", status="processing", metadata={"rows": 100, "started_at": datetime.now().isoformat()}
    )

    await sqlite_job_saver.update_progress("test-job-001", "validation", 0.5)
    await sqlite_job_saver.update_progress("test-job-001", "prediction", 0.8)

    status = await sqlite_job_saver.get_status("test-job-001")
    print(f"Retrieved status: {status}")

    print("\n2. Testing API SchemaCollector...")

    # Test schema operations
    available_schemas = await api_schema_collector.get_available_schemas()
    print(f"Available schemas: {len(available_schemas)}")
    for schema in available_schemas:
        print(f"  - {schema.core_name} + {schema.program_name}")

    # Get schema details
    schema = await api_schema_collector.get_schema("prog-001", "core-001")
    columns = await api_schema_collector.get_schema_columns("prog-001", "core-001")
    rules = await api_schema_collector.get_validation_rules("prog-001", "core-001")

    print(f"Schema columns: {columns}")
    print(f"Validation rules: {json.dumps(rules, indent=2)}")

    print("\n3. Testing with MetadataHarmonizationProcessor...")

    # Create processor with custom implementations
    session_id = f"custom-impl-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        job_status_saver=sqlite_job_saver,
        schema_collector=api_schema_collector,
        session_id=session_id,
        config_path="examples/config-basic.yaml",
    )

    try:
        # Create sample data matching the mock schema
        sample_data = {
            "patient_id": ["P001", "P002", "P003"],
            "age": ["25", "invalid_age", "45"],
            "test_result": ["positive", "unknown", "negative"],  # 'unknown' is invalid
            "test_date": ["2024-01-15", "2024/01/16", "2024-01-17"],  # middle one has wrong format
        }
        metadata_df = pd.DataFrame(sample_data)

        print(f"Processing {len(metadata_df)} rows with custom implementations...")

        # Process through pipeline
        results = await processor.process(metadata_df, program_id="prog-001", core_id="core-001")

        # Display results
        print("\nResults:")
        print(f"  Total errors: {results.summary.total_errors}")
        print(f"  Error types: {results.summary.error_types}")

        if results.validation_results:
            print("\nValidation errors:")
            for error in results.validation_results:
                print(f"  Row {error.row}, Column '{error.column}': {error.error_type}")
                print(f"    Current: '{error.current_value}'")
                if error.recommended_value:
                    print(f"    Recommended: '{error.recommended_value}'")
                if error.valid_options:
                    print(f"    Valid options: {error.valid_options}")

        # Check final job status
        state = processor.get_current_state()
        if state:
            final_status = await sqlite_job_saver.get_status(state.job_id)
            print(f"\nFinal job status: {final_status}")

    finally:
        await processor.cleanup()

    print("\nCustom implementations demo completed!")


async def demonstrate_interface_contracts():
    """Demonstrate the interface contracts and error handling."""

    print("\n=== Interface Contracts Demo ===")

    # Test interface contract compliance
    sqlite_saver = SQLiteJobStatusSaver("./examples/test_contracts.db")
    api_collector = APISchemaCollector("https://api.example.com")

    # Test JobStatusSaver contract
    print("Testing JobStatusSaver interface contract...")

    # Test with various data types
    test_metadata = {
        "string_value": "test",
        "numeric_value": 123,
        "boolean_value": True,
        "list_value": [1, 2, 3],
        "dict_value": {"nested": "data"},
    }

    await sqlite_saver.save_status("contract-test", "testing", test_metadata)
    retrieved = await sqlite_saver.get_status("contract-test")

    print(f"Metadata round-trip successful: {retrieved['metadata'] == test_metadata}")

    # Test SchemaCollector contract
    print("Testing SchemaCollector interface contract...")

    schemas = await api_collector.get_available_schemas()
    print(f"SchemaInfo objects returned: {all(isinstance(s, SchemaInfo) for s in schemas)}")

    if schemas:
        first_schema = schemas[0]
        schema_def = await api_collector.get_schema(first_schema.program_uuid, first_schema.core_uuid)
        columns = await api_collector.get_schema_columns(first_schema.program_uuid, first_schema.core_uuid)
        rules = await api_collector.get_validation_rules(first_schema.program_uuid, first_schema.core_uuid)

        print(f"Schema definition is dict: {isinstance(schema_def, dict)}")
        print(f"Columns is list of strings: {isinstance(columns, list) and all(isinstance(c, str) for c in columns)}")
        print(f"Rules is dict: {isinstance(rules, dict)}")

    print("Interface contracts verified!")


if __name__ == "__main__":

    async def main():
        """Run all custom implementation examples."""
        await demonstrate_custom_implementations()
        await demonstrate_interface_contracts()
        print("\nAll custom implementation examples completed!")

    asyncio.run(main())
