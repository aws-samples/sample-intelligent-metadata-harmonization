# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for FileBasedSchemaCollector implementation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from metadata_harmonization_processor.implementations.file_schema_collector import (
    FileBasedSchemaCollector,
)


class TestFileBasedSchemaCollector:
    """Test cases for FileBasedSchemaCollector."""

    @pytest.fixture
    def mock_catalog_data(self):
        """Mock catalog.json data."""
        return [
            {
                "core_uuid": "core-123",
                "core_name": "Test Core Schema",
                "core_path": "test_core.json",
                "program": [
                    {
                        "program_uuid": "program-456",
                        "program_name": "Test Program Schema",
                        "program_path": "test_program.json",
                    },
                    {
                        "program_uuid": "program-789",
                        "program_name": "Another Program Schema",
                        "program_path": "another_program.json",
                    },
                ],
            },
            {
                "core_uuid": "core-999",
                "core_name": "Another Core Schema",
                "core_path": "another_core.json",
                "program": [
                    {
                        "program_uuid": "program-111",
                        "program_name": "Third Program Schema",
                        "program_path": "third_program.json",
                    }
                ],
            },
        ]

    @pytest.fixture
    def mock_core_schema(self):
        """Mock core schema data."""
        return {
            "$id": "https://example.com/core.schema.json",
            "type": "object",
            "title": "Core Schema",
            "description": "Core metadata schema",
            "required": ["field1", "field2"],
            "properties": {
                "field1": {"type": "string", "minLength": 1},
                "field2": {"type": "string", "enum": ["option1", "option2", "option3"]},
            },
        }

    @pytest.fixture
    def mock_program_schema(self):
        """Mock program schema data."""
        return {
            "$id": "https://example.com/program.schema.json",
            "type": "object",
            "title": "Program Schema",
            "description": "Program-specific metadata schema",
            "required": ["field3"],
            "properties": {
                "field2": {
                    "type": "string",
                    "enum": [
                        "option1",
                        "option2",
                        "option3",
                        "option4",
                    ],  # Extended options
                },
                "field3": {"type": "string", "pattern": "^[A-Z]{2,3}$"},
                "field4": {"type": "integer", "minimum": 0, "maximum": 100},
            },
        }

    @patch("pathlib.Path.exists")
    def test_init_success(self, mock_exists):
        """Test successful initialization."""
        mock_exists.return_value = True

        collector = FileBasedSchemaCollector("/test/schema/dir")

        assert collector.schema_directory == Path("/test/schema/dir")
        assert collector.catalog_path == Path("/test/schema/dir/catalog.json")
        assert collector._catalog_cache is None
        assert collector._schema_cache == {}

    @patch("pathlib.Path.exists")
    def test_init_directory_not_found(self, mock_exists):
        """Test initialization with missing directory."""
        mock_exists.side_effect = lambda: False  # Directory doesn't exist

        with pytest.raises(FileNotFoundError, match="Schema directory not found"):
            FileBasedSchemaCollector("/nonexistent/dir")

    def test_init_catalog_not_found(self):
        """Test initialization with missing catalog.json."""
        with patch("metadata_harmonization_processor.implementations.file_schema_collector.Path") as MockPath:
            # Create mock Path instances
            mock_dir_path = MagicMock(spec=Path)
            mock_catalog_path = MagicMock(spec=Path)

            # Set up string representations
            mock_dir_path.__str__.return_value = "/test/schema/dir"
            mock_catalog_path.__str__.return_value = "/test/schema/dir/catalog.json"

            # Set up exists() return values - directory exists, catalog doesn't
            mock_dir_path.exists.return_value = True
            mock_catalog_path.exists.return_value = False

            # Set up truediv operator (/) to return catalog path
            mock_dir_path.__truediv__.return_value = mock_catalog_path

            # Mock iterdir() to return empty list
            mock_dir_path.iterdir.return_value = []

            # Set up Path constructor to return our mock directory
            MockPath.return_value = mock_dir_path

            with pytest.raises(FileNotFoundError, match="Catalog file not found"):
                FileBasedSchemaCollector("/test/schema/dir")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_available_schemas_success(self, mock_file, mock_exists, mock_catalog_data):
        """Test successful retrieval of available schemas."""
        mock_file.return_value.read.return_value = json.dumps(mock_catalog_data)

        collector = FileBasedSchemaCollector("/test/schema/dir")
        schemas = await collector.get_available_schemas()

        assert len(schemas) == 3

        # Check first schema
        assert schemas[0].core_uuid == "core-123"
        assert schemas[0].core_name == "Test Core Schema"
        assert schemas[0].core_path == "test_core.json"
        assert schemas[0].program_uuid == "program-456"
        assert schemas[0].program_name == "Test Program Schema"
        assert schemas[0].program_path == "test_program.json"

        # Check second schema (same core, different program)
        assert schemas[1].core_uuid == "core-123"
        assert schemas[1].program_uuid == "program-789"

        # Check third schema (different core)
        assert schemas[2].core_uuid == "core-999"
        assert schemas[2].program_uuid == "program-111"

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_available_schemas_invalid_json(self, mock_file, mock_exists):
        """Test handling of invalid JSON in catalog."""
        mock_file.return_value.read.return_value = "invalid json"

        collector = FileBasedSchemaCollector("/test/schema/dir")

        with pytest.raises(json.JSONDecodeError):
            await collector.get_available_schemas()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_available_schemas_missing_fields(self, mock_file, mock_exists):
        """Test handling of catalog entries with missing required fields."""
        invalid_catalog = [
            {
                "core_uuid": "core-123",
                # Missing core_name, core_path, program
            },
            {
                "core_uuid": "core-456",
                "core_name": "Valid Core",
                "core_path": "valid_core.json",
                "program": [
                    {
                        "program_uuid": "program-789",
                        # Missing program_name, program_path
                    }
                ],
            },
        ]
        mock_file.return_value.read.return_value = json.dumps(invalid_catalog)

        collector = FileBasedSchemaCollector("/test/schema/dir")
        schemas = await collector.get_available_schemas()

        # Should return empty list as all entries are invalid
        assert len(schemas) == 0

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_schema_success(
        self,
        mock_file,
        mock_exists,
        mock_catalog_data,
        mock_core_schema,
        mock_program_schema,
    ):
        """Test successful schema combination."""

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data=json.dumps(mock_core_schema)).return_value
            elif file_path_str.endswith("test_program.json"):
                return mock_open(read_data=json.dumps(mock_program_schema)).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")
            combined_schema = await collector.get_schema("program-456", "core-123")

        # Check that schemas were combined correctly
        assert "properties" in combined_schema
        assert len(combined_schema["properties"]) == 4  # field1, field2 (overridden), field3, field4

        # Check that program schema overrode core schema for field2
        assert combined_schema["properties"]["field2"]["enum"] == [
            "option1",
            "option2",
            "option3",
            "option4",
        ]

        # Check that required fields were merged
        assert set(combined_schema["required"]) == {"field1", "field2", "field3"}

        # Check title was updated
        assert "Combined" in combined_schema["title"]

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_schema_not_found(self, mock_file, mock_exists, mock_catalog_data):
        """Test handling of schema IDs not found in catalog."""
        mock_file.return_value.read.return_value = json.dumps(mock_catalog_data)

        collector = FileBasedSchemaCollector("/test/schema/dir")

        with pytest.raises(ValueError, match="Schema combination not found"):
            await collector.get_schema("nonexistent-program", "nonexistent-core")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_schema_columns_success(
        self,
        mock_file,
        mock_exists,
        mock_catalog_data,
        mock_core_schema,
        mock_program_schema,
    ):
        """Test successful retrieval of schema columns."""

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data=json.dumps(mock_core_schema)).return_value
            elif file_path_str.endswith("test_program.json"):
                return mock_open(read_data=json.dumps(mock_program_schema)).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")
            columns = await collector.get_schema_columns("program-456", "core-123")

        # Should return all properties from combined schema
        assert set(columns) == {"field1", "field2", "field3", "field4"}

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_get_validation_rules_success(
        self,
        mock_file,
        mock_exists,
        mock_catalog_data,
        mock_core_schema,
        mock_program_schema,
    ):
        """Test successful retrieval of validation rules."""

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data=json.dumps(mock_core_schema)).return_value
            elif file_path_str.endswith("test_program.json"):
                return mock_open(read_data=json.dumps(mock_program_schema)).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")
            rules = await collector.get_validation_rules("program-456", "core-123")

        # Check field1 rules (from core schema)
        assert rules["field1"]["type"] == "string"
        assert rules["field1"]["min_length"] == 1
        assert rules["field1"]["required"] is True

        # Check field2 rules (overridden by program schema)
        assert rules["field2"]["type"] == "string"
        assert rules["field2"]["options"] == [
            "option1",
            "option2",
            "option3",
            "option4",
        ]
        assert rules["field2"]["required"] is True

        # Check field3 rules (from program schema)
        assert rules["field3"]["type"] == "string"
        assert rules["field3"]["pattern"] == "^[A-Z]{2,3}$"
        assert rules["field3"]["required"] is True

        # Check field4 rules (from program schema, not required)
        assert rules["field4"]["type"] == "integer"
        assert rules["field4"]["required"] is False

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_caching_behavior(self, mock_file, mock_exists, mock_catalog_data, mock_core_schema):
        """Test that catalog and schema files are cached properly."""
        call_count = 0

        def mock_open_side_effect(file_path, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data=json.dumps(mock_core_schema)).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")

            # First call should load from file
            await collector.get_available_schemas()
            first_call_count = call_count

            # Second call should use cache
            await collector.get_available_schemas()
            second_call_count = call_count

            # Should not have made additional file calls
            assert second_call_count == first_call_count

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_schema_file_not_found(self, mock_file, mock_exists, mock_catalog_data):
        """Test handling of missing schema files."""

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")

            with pytest.raises(FileNotFoundError):
                await collector.get_schema("program-456", "core-123")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_invalid_schema_json(self, mock_file, mock_exists, mock_catalog_data):
        """Test handling of invalid JSON in schema files."""

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(mock_catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data="invalid json").return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")

            with pytest.raises(json.JSONDecodeError):
                await collector.get_schema("program-456", "core-123")

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    async def test_complex_validation_rules(self, mock_file, mock_exists):
        """Test extraction of complex validation rules including AMD validation."""
        catalog_data = [
            {
                "core_uuid": "core-123",
                "core_name": "Test Core",
                "core_path": "test_core.json",
                "program": [
                    {
                        "program_uuid": "program-456",
                        "program_name": "Test Program",
                        "program_path": "test_program.json",
                    }
                ],
            }
        ]

        complex_schema = {
            "type": "object",
            "required": ["field1", "field2"],
            "properties": {
                "field1": {
                    "type": "string",
                    "amdValidation": "amd-valid-dates",
                    "errorMessage": {"type": "Field must be a valid date"},
                },
                "field2": {
                    "type": "string",
                    "amdValidation": "amd-depends-on,amd-parent-child-enum",
                    "amdValidationOptions": {
                        "amd-depends-on": "field1",
                        "amd-parent-child-enum": {
                            "parentKey": "field1",
                            "parentChildData": {
                                "parent1": ["child1", "child2"],
                                "parent2": ["child3", "child4"],
                            },
                        },
                    },
                    "errorMessage": {"enum": "Invalid option selected"},
                },
            },
        }

        def mock_open_side_effect(file_path, *args, **kwargs):
            file_path_str = str(file_path)
            if file_path_str.endswith("catalog.json"):
                return mock_open(read_data=json.dumps(catalog_data)).return_value
            elif file_path_str.endswith("test_core.json"):
                return mock_open(read_data=json.dumps(complex_schema)).return_value
            elif file_path_str.endswith("test_program.json"):
                return mock_open(read_data=json.dumps({"type": "object", "properties": {}})).return_value
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        with patch("builtins.open", side_effect=mock_open_side_effect):
            collector = FileBasedSchemaCollector("/test/schema/dir")
            rules = await collector.get_validation_rules("program-456", "core-123")

        # Check AMD validation rules were extracted
        assert rules["field1"]["amd_validation"] == "amd-valid-dates"
        assert rules["field1"]["error_message"]["type"] == "Field must be a valid date"

        assert rules["field2"]["amd_validation"] == "amd-depends-on,amd-parent-child-enum"
        assert "amd_validation_options" in rules["field2"]
        assert rules["field2"]["amd_validation_options"]["amd-depends-on"] == "field1"
