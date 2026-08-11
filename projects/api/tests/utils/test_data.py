# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Test data utilities and factories."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from metadata_harmonization_processor.models.validation import ValidationErrorType


class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_metadata_schema(
        core_schema_id: str = "test_core_v1",
        name: str = "Test Core Schema",
        program_schemas: Optional[List[Dict]] = None,
    ) -> Dict:
        """Create a test metadata schema."""
        if program_schemas is None:
            program_schemas = [
                {
                    "program_name": "Test Program",
                    "s3_location": "schemas/programs/test/v1.0/schema.json",
                    "s3_bucket": "test-schemas",
                    "program_schema_id": "test_program_v1",
                }
            ]

        return {
            "core_schema_id": core_schema_id,
            "name": name,
            "core_schema_path": f"schemas/core/{core_schema_id}/schema.json",
            "core_schema_s3_bucket": "test-schemas",
            "program_schemas": program_schemas,
        }

    @staticmethod
    def create_upload_job(
        job_id: Optional[str] = None,
        user_id: str = "test_user",
        status: str = "pending",
        core_schema_id: str = "test_core_v1",
        program_schema_id: str = "test_program_v1",
        current_version: int = 1,
        results: Optional[Dict] = None,
    ) -> Dict:
        """Create a test upload job."""
        if job_id is None:
            job_id = str(uuid4())

        if results is None:
            results = {}

        return {
            "job_id": job_id,
            "user_id": user_id,
            "core_schema_id": core_schema_id,
            "program_schema_id": program_schema_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None if status != "completed" else datetime.now(timezone.utc).isoformat(),
            "current_version": current_version,
            "results": results,
        }

    @staticmethod
    def create_validation_results(
        total_rows: int = 10, total_errors: int = 2, validation_errors: Optional[List[Dict]] = None
    ) -> Dict:
        """Create test validation results."""
        if validation_errors is None:
            validation_errors = [
                {
                    "row": 1,
                    "column": "participant_id",
                    "current_value": "",
                    "valid_options": None,
                    "recommended_value": None,
                    "error_type": ValidationErrorType.REQUIRED_VALUE.value,
                },
                {
                    "row": 3,
                    "column": "city",
                    "current_value": "NYC",
                    "valid_options": ["New York City", "Brooklyn", "Queens"],
                    "recommended_value": "New York City",
                    "error_type": ValidationErrorType.INVALID_OPTION.value,
                },
            ]

        error_type_counts = {}
        for error in validation_errors:
            error_type = error["error_type"]
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        columns_validated = len({e["column"] for e in validation_errors if "column" in e})
        return {
            "validation_results": validation_errors,
            "summary": {
                "total_rows": total_rows,
                "total_errors": total_errors,
                "error_types": error_type_counts,
                "columns_validated": columns_validated,
            },
        }

    @staticmethod
    def create_csv_content(
        headers: List[str] = None, rows: List[List[str]] = None, include_errors: bool = False
    ) -> str:
        """Create test CSV content."""
        if headers is None:
            headers = ["participant_id", "age", "city", "state"]

        if rows is None:
            if include_errors:
                rows = [
                    ["", "25", "New York City", "NY"],  # Missing participant_id
                    ["DEF456", "30", "NYC", "CA"],  # Invalid city format
                    ["GHI789", "35", "Chicago", "IL"],  # Valid row
                ]
            else:
                rows = [
                    ["ABC123", "25", "New York City", "NY"],
                    ["DEF456", "30", "Los Angeles", "CA"],
                    ["GHI789", "35", "Chicago", "IL"],
                ]

        lines = [",".join(headers)]
        for row in rows:
            lines.append(",".join(row))

        return "\n".join(lines)

    @staticmethod
    def create_validation_request(
        core_schema_id: str = "test_core_v1", program_schema_id: str = "test_program_v1"
    ) -> Dict:
        """Create a test validation request."""
        return {"core_schema_id": core_schema_id, "program_schema_id": program_schema_id}

    @staticmethod
    def create_json_content(data: Dict) -> str:
        """Create JSON content from a dictionary."""
        return json.dumps(data, indent=2)


class DynamoDBTestHelper:
    """Helper for DynamoDB test operations."""

    @staticmethod
    def format_dynamodb_item(item: Dict) -> Dict:
        """Format a Python dict as a DynamoDB item."""

        def format_value(value):
            if isinstance(value, str):
                return {"S": value}
            elif isinstance(value, int):
                return {"N": str(value)}
            elif isinstance(value, bool):
                return {"BOOL": value}
            elif isinstance(value, list):
                return {"L": [format_value(v) for v in value]}
            elif isinstance(value, dict):
                return {"M": {k: format_value(v) for k, v in value.items()}}
            elif value is None:
                return {"NULL": True}
            else:
                return {"S": str(value)}

        return {k: format_value(v) for k, v in item.items()}

    @staticmethod
    def parse_dynamodb_item(item: Dict) -> Dict:
        """Parse a DynamoDB item to a Python dict."""

        def parse_value(value):
            if "S" in value:
                return value["S"]
            elif "N" in value:
                return int(value["N"]) if value["N"].isdigit() else float(value["N"])
            elif "BOOL" in value:
                return value["BOOL"]
            elif "L" in value:
                return [parse_value(v) for v in value["L"]]
            elif "M" in value:
                return {k: parse_value(v) for k, v in value["M"].items()}
            elif "NULL" in value:
                return None
            else:
                return str(value)

        return {k: parse_value(v) for k, v in item.items()}


class S3TestHelper:
    """Helper for S3 test operations."""

    @staticmethod
    def create_s3_response(content: str, content_type: str = "application/json") -> Dict:
        """Create a mock S3 response."""
        from io import BytesIO

        body_mock = BytesIO(content.encode())
        return {
            "Body": body_mock,
            "ContentType": content_type,
            "ContentLength": len(content),
            "LastModified": datetime.now(timezone.utc),
        }

    @staticmethod
    def create_validation_results_s3_content(validation_results: Dict) -> str:
        """Create S3 content for validation results."""
        return json.dumps(validation_results, indent=2)


class FileTestHelper:
    """Helper for file testing operations."""

    @staticmethod
    def create_upload_file_mock(filename: str, content: str, content_type: str = "text/csv"):
        """Create a mock UploadFile for testing."""
        from unittest.mock import MagicMock, AsyncMock

        mock_file = MagicMock()
        mock_file.filename = filename
        mock_file.content_type = content_type
        mock_file.size = len(content)

        # Create a mock file object with seek method
        mock_file_obj = MagicMock()
        mock_file_obj.seek = MagicMock(return_value=None)
        mock_file.file = mock_file_obj

        mock_file.read = AsyncMock(return_value=content.encode())
        mock_file.seek = MagicMock(return_value=None)

        return mock_file

    @staticmethod
    def get_file_size_mb(content: str) -> float:
        """Get file size in MB."""
        return len(content.encode()) / (1024 * 1024)


# Common test constants
TEST_SCHEMAS = [
    TestDataFactory.create_metadata_schema(
        core_schema_id="core_v1",
        name="Core Schema v1",
        program_schemas=[
            {
                "program_name": "Cancer Registry",
                "s3_location": "schemas/programs/cancer/v1.0/schema.json",
                "s3_bucket": "test-schemas",
                "program_schema_id": "cancer_v1",
            },
            {
                "program_name": "Birth Defects",
                "s3_location": "schemas/programs/birth_defects/v1.0/schema.json",
                "s3_bucket": "test-schemas",
                "program_schema_id": "birth_defects_v1",
            },
        ],
    ),
    TestDataFactory.create_metadata_schema(
        core_schema_id="core_v2",
        name="Core Schema v2",
        program_schemas=[
            {
                "program_name": "Flu Surveillance",
                "s3_location": "schemas/programs/flu/v2.0/schema.json",
                "s3_bucket": "test-schemas",
                "program_schema_id": "flu_v2",
            }
        ],
    ),
]

TEST_CSV_VALID = TestDataFactory.create_csv_content()
TEST_CSV_WITH_ERRORS = TestDataFactory.create_csv_content(include_errors=True)
TEST_VALIDATION_RESULTS = TestDataFactory.create_validation_results()
