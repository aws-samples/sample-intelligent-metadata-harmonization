# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for SchemaCollector interface contract."""

from abc import ABC
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from metadata_harmonization_processor.interfaces.schema_collector import (
    SchemaCollector,
    SchemaInfo,
)


class MockSchemaCollector(SchemaCollector):
    """Mock implementation of SchemaCollector for testing interface contract."""

    def __init__(self):
        self.schemas = [
            SchemaInfo(
                core_uuid="core_1",
                core_name="Test Core Schema",
                core_path="schemas/core_1.json",
                program_uuid="program_1",
                program_name="Test Program Schema",
                program_path="schemas/program_1.json",
            )
        ]
        # Create AsyncMock instances for tracking calls
        self._get_available_schemas_mock = AsyncMock()
        self._get_schema_mock = AsyncMock()
        self._get_schema_columns_mock = AsyncMock()
        self._get_validation_rules_mock = AsyncMock()

    async def get_available_schemas(self) -> List[SchemaInfo]:
        """Mock implementation of get_available_schemas."""
        await self._get_available_schemas_mock()
        return self.schemas

    async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Mock implementation of get_schema."""
        await self._get_schema_mock(program_id, core_id)
        return {"type": "object", "properties": {}}

    async def get_schema_columns(self, program_id: str, core_id: str) -> List[str]:
        """Mock implementation of get_schema_columns."""
        await self._get_schema_columns_mock(program_id, core_id)
        return ["column1", "column2"]

    async def get_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Mock implementation of get_validation_rules."""
        await self._get_validation_rules_mock(program_id, core_id)
        return {"column1": {"required": True}}


class TestSchemaInfo:
    """Test cases for SchemaInfo Pydantic model."""

    def test_schema_info_creation(self):
        """Test SchemaInfo model creation with valid data."""
        schema_info = SchemaInfo(
            core_uuid="core_123",
            core_name="Core Schema",
            core_path="schemas/core.json",
            program_uuid="program_456",
            program_name="Program Schema",
            program_path="schemas/program.json",
        )

        assert schema_info.core_uuid == "core_123"
        assert schema_info.core_name == "Core Schema"
        assert schema_info.core_path == "schemas/core.json"
        assert schema_info.program_uuid == "program_456"
        assert schema_info.program_name == "Program Schema"
        assert schema_info.program_path == "schemas/program.json"

    def test_schema_info_validation(self):
        """Test SchemaInfo model validation."""
        # Should require all fields
        with pytest.raises(ValueError):
            SchemaInfo()

        # Should validate field types
        with pytest.raises(ValueError):
            SchemaInfo(
                core_uuid=123,  # Should be string
                core_name="Core Schema",
                core_path="schemas/core.json",
                program_uuid="program_456",
                program_name="Program Schema",
                program_path="schemas/program.json",
            )

    def test_schema_info_serialization(self):
        """Test SchemaInfo model serialization."""
        schema_info = SchemaInfo(
            core_uuid="core_123",
            core_name="Core Schema",
            core_path="schemas/core.json",
            program_uuid="program_456",
            program_name="Program Schema",
            program_path="schemas/program.json",
        )

        # Should serialize to dict
        data = schema_info.model_dump()
        expected = {
            "core_uuid": "core_123",
            "core_name": "Core Schema",
            "core_path": "schemas/core.json",
            "program_uuid": "program_456",
            "program_name": "Program Schema",
            "program_path": "schemas/program.json",
        }
        assert data == expected

        # Should serialize to JSON
        json_str = schema_info.model_dump_json()
        assert isinstance(json_str, str)
        assert "core_123" in json_str


class TestSchemaCollector:
    """Test cases for SchemaCollector interface contract."""

    def test_is_abstract_base_class(self):
        """Test that SchemaCollector is an abstract base class."""
        assert issubclass(SchemaCollector, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            SchemaCollector()

    def test_has_required_abstract_methods(self):
        """Test that SchemaCollector has all required abstract methods."""
        abstract_methods = SchemaCollector.__abstractmethods__
        expected_methods = {
            "get_available_schemas",
            "get_schema",
            "get_schema_columns",
            "get_validation_rules",
        }

        assert abstract_methods == expected_methods

    @pytest.mark.asyncio
    async def test_get_available_schemas_interface(self):
        """Test get_available_schemas method interface contract."""
        collector = MockSchemaCollector()

        result = await collector.get_available_schemas()

        # Should return a list of SchemaInfo objects
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(schema, SchemaInfo) for schema in result)

        # Verify the mock was called
        collector._get_available_schemas_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_schema_interface(self):
        """Test get_schema method interface contract."""
        collector = MockSchemaCollector()

        program_id = "program_1"
        core_id = "core_1"

        result = await collector.get_schema(program_id, core_id)

        # Should return a dictionary
        assert isinstance(result, dict)

        # Verify the mock was called with correct parameters
        collector._get_schema_mock.assert_called_once_with(program_id, core_id)

    @pytest.mark.asyncio
    async def test_get_schema_columns_interface(self):
        """Test get_schema_columns method interface contract."""
        collector = MockSchemaCollector()

        program_id = "program_1"
        core_id = "core_1"

        result = await collector.get_schema_columns(program_id, core_id)

        # Should return a list of strings
        assert isinstance(result, list)
        assert all(isinstance(col, str) for col in result)

        # Verify the mock was called with correct parameters
        collector._get_schema_columns_mock.assert_called_once_with(program_id, core_id)

    @pytest.mark.asyncio
    async def test_get_validation_rules_interface(self):
        """Test get_validation_rules method interface contract."""
        collector = MockSchemaCollector()

        program_id = "program_1"
        core_id = "core_1"

        result = await collector.get_validation_rules(program_id, core_id)

        # Should return a dictionary
        assert isinstance(result, dict)

        # Verify the mock was called with correct parameters
        collector._get_validation_rules_mock.assert_called_once_with(program_id, core_id)

    @pytest.mark.asyncio
    async def test_method_signatures(self):
        """Test that all methods have correct signatures."""
        collector = MockSchemaCollector()

        # Test get_available_schemas signature
        schemas = await collector.get_available_schemas()
        assert isinstance(schemas, list)

        # Test get_schema signature
        schema = await collector.get_schema("program_id", "core_id")
        assert isinstance(schema, dict)

        # Test get_schema_columns signature
        columns = await collector.get_schema_columns("program_id", "core_id")
        assert isinstance(columns, list)

        # Test get_validation_rules signature
        rules = await collector.get_validation_rules("program_id", "core_id")
        assert isinstance(rules, dict)

    def test_concrete_implementation_requirements(self):
        """Test that concrete implementations must implement all abstract methods."""

        class IncompleteImplementation(SchemaCollector):
            """Incomplete implementation missing required methods."""

            async def get_available_schemas(self) -> List[SchemaInfo]:
                return []

            # Missing other required methods

        # Should not be able to instantiate incomplete implementation
        with pytest.raises(TypeError):
            IncompleteImplementation()

    @pytest.mark.asyncio
    async def test_error_handling_contract(self):
        """Test that implementations can raise exceptions as documented."""

        class ErrorRaisingImplementation(SchemaCollector):
            """Implementation that raises exceptions for testing."""

            async def get_available_schemas(self) -> List[SchemaInfo]:
                raise Exception("Get available schemas failed")

            async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
                raise Exception("Get schema failed")

            async def get_schema_columns(self, program_id: str, core_id: str) -> List[str]:
                raise Exception("Get schema columns failed")

            async def get_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]:
                raise Exception("Get validation rules failed")

        collector = ErrorRaisingImplementation()

        # All methods should be able to raise exceptions
        with pytest.raises(Exception, match="Get available schemas failed"):
            await collector.get_available_schemas()

        with pytest.raises(Exception, match="Get schema failed"):
            await collector.get_schema("program_id", "core_id")

        with pytest.raises(Exception, match="Get schema columns failed"):
            await collector.get_schema_columns("program_id", "core_id")

        with pytest.raises(Exception, match="Get validation rules failed"):
            await collector.get_validation_rules("program_id", "core_id")

    @pytest.mark.asyncio
    async def test_schema_info_in_available_schemas(self):
        """Test that get_available_schemas returns proper SchemaInfo objects."""
        collector = MockSchemaCollector()

        schemas = await collector.get_available_schemas()

        for schema in schemas:
            assert isinstance(schema, SchemaInfo)
            assert hasattr(schema, "core_uuid")
            assert hasattr(schema, "core_name")
            assert hasattr(schema, "core_path")
            assert hasattr(schema, "program_uuid")
            assert hasattr(schema, "program_name")
            assert hasattr(schema, "program_path")

            # All fields should be strings
            assert isinstance(schema.core_uuid, str)
            assert isinstance(schema.core_name, str)
            assert isinstance(schema.core_path, str)
            assert isinstance(schema.program_uuid, str)
            assert isinstance(schema.program_name, str)
            assert isinstance(schema.program_path, str)
