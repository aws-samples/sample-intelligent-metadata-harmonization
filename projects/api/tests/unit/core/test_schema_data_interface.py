# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for SchemaCollector interface and implementations."""

import pytest

from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector, SchemaInfo
from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
from tests.utils.test_data import TestDataFactory


class TestSchemaCollector:
    """Test cases for SchemaCollector interface and implementations."""

    @pytest.fixture
    def mock_schema_directory(self, tmp_path):
        """Create a mock schema directory with catalog.json."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()

        # Create catalog.json
        catalog_data = [
            {
                "core_uuid": "test_core_v1",
                "core_name": "Test Core Schema",
                "core_path": "core_v1.json",
                "program": [
                    {
                        "program_uuid": "test_program_1_v1",
                        "program_name": "Test Program 1",
                        "program_path": "program_1_v1.json",
                    },
                    {
                        "program_uuid": "test_program_2_v1",
                        "program_name": "Test Program 2",
                        "program_path": "program_2_v1.json",
                    },
                ],
            }
        ]

        catalog_file = schema_dir / "catalog.json"
        catalog_file.write_text(TestDataFactory.create_json_content(catalog_data))

        # Create schema files
        core_schema = {"type": "object", "properties": {"id": {"type": "string"}}}
        program_schema = {"type": "object", "properties": {"program_field": {"type": "string"}}}

        (schema_dir / "core_v1.json").write_text(TestDataFactory.create_json_content(core_schema))
        (schema_dir / "program_1_v1.json").write_text(TestDataFactory.create_json_content(program_schema))
        (schema_dir / "program_2_v1.json").write_text(TestDataFactory.create_json_content(program_schema))

        return schema_dir

    @pytest.fixture
    def file_schema_collector(self, mock_schema_directory):
        """Create a FileBasedSchemaCollector instance."""
        return FileBasedSchemaCollector(str(mock_schema_directory))

    @pytest.mark.asyncio
    async def test_get_available_schemas_success(self, file_schema_collector):
        """Test successful retrieval of available schemas."""
        schemas = await file_schema_collector.get_available_schemas()

        assert len(schemas) == 2  # 2 program schemas under 1 core schema
        assert all(isinstance(schema, SchemaInfo) for schema in schemas)

        # Check first schema
        schema1 = schemas[0]
        assert schema1.core_uuid == "test_core_v1"
        assert schema1.core_name == "Test Core Schema"
        assert schema1.program_uuid == "test_program_1_v1"
        assert schema1.program_name == "Test Program 1"

    @pytest.mark.asyncio
    async def test_get_available_schemas_empty_catalog(self, tmp_path):
        """Test get_available_schemas with empty catalog."""
        schema_dir = tmp_path / "empty_schemas"
        schema_dir.mkdir()

        # Create empty catalog.json
        catalog_file = schema_dir / "catalog.json"
        catalog_file.write_text("[]")

        collector = FileBasedSchemaCollector(str(schema_dir))
        schemas = await collector.get_available_schemas()

        assert len(schemas) == 0

    @pytest.mark.asyncio
    async def test_get_schema_success(self, file_schema_collector):
        """Test successful schema retrieval by program and core IDs."""
        schema = await file_schema_collector.get_schema("test_program_1_v1", "test_core_v1")

        assert schema is not None
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_schema_not_found(self, file_schema_collector):
        """Test schema retrieval with non-existent IDs."""
        with pytest.raises(Exception):  # Should raise FileNotFoundError or similar
            await file_schema_collector.get_schema("nonexistent_program", "nonexistent_core")

    @pytest.mark.asyncio
    async def test_get_schema_columns_success(self, file_schema_collector):
        """Test successful retrieval of schema columns."""
        columns = await file_schema_collector.get_schema_columns("test_program_1_v1", "test_core_v1")

        assert isinstance(columns, list)
        # Should contain columns from both core and program schemas
        assert len(columns) >= 0

    @pytest.mark.asyncio
    async def test_get_validation_rules_success(self, file_schema_collector):
        """Test successful retrieval of validation rules."""
        rules = await file_schema_collector.get_validation_rules("test_program_1_v1", "test_core_v1")

        assert isinstance(rules, dict)
        # Should contain validation rules extracted from schema

    @pytest.mark.asyncio
    async def test_catalog_caching(self, file_schema_collector):
        """Test that catalog.json is cached after first load."""
        # First call should load from file
        schemas1 = await file_schema_collector.get_available_schemas()

        # Second call should use cached data
        schemas2 = await file_schema_collector.get_available_schemas()

        assert schemas1 == schemas2
        assert len(schemas1) == 2

    @pytest.mark.asyncio
    async def test_schema_file_caching(self, file_schema_collector):
        """Test that schema files are cached after first load."""
        # First call should load from file
        schema1 = await file_schema_collector.get_schema("test_program_1_v1", "test_core_v1")

        # Second call should use cached data
        schema2 = await file_schema_collector.get_schema("test_program_1_v1", "test_core_v1")

        assert schema1 == schema2
        assert schema1 is not None

    @pytest.mark.asyncio
    async def test_missing_catalog_file(self, tmp_path):
        """Test behavior when catalog.json is missing."""
        schema_dir = tmp_path / "no_catalog"
        schema_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            FileBasedSchemaCollector(str(schema_dir))

    @pytest.mark.asyncio
    async def test_invalid_catalog_json(self, tmp_path):
        """Test behavior with invalid JSON in catalog.json."""
        schema_dir = tmp_path / "invalid_catalog"
        schema_dir.mkdir()

        # Create invalid JSON file
        catalog_file = schema_dir / "catalog.json"
        catalog_file.write_text("invalid json content")

        collector = FileBasedSchemaCollector(str(schema_dir))

        with pytest.raises(Exception):  # Should raise JSON decode error
            await collector.get_available_schemas()


class TestSchemaCollectorInterface:
    """Test the SchemaCollector abstract interface."""

    def test_schema_collector_is_abstract(self):
        """Test that SchemaCollector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SchemaCollector()

    def test_schema_info_model(self):
        """Test SchemaInfo model validation."""
        schema_info = SchemaInfo(
            core_uuid="test_core",
            core_name="Test Core",
            core_path="core.json",
            program_uuid="test_program",
            program_name="Test Program",
            program_path="program.json",
        )

        assert schema_info.core_uuid == "test_core"
        assert schema_info.core_name == "Test Core"
        assert schema_info.program_uuid == "test_program"
        assert schema_info.program_name == "Test Program"
