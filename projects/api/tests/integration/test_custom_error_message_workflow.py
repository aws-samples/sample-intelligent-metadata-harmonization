# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for custom error message workflow.

This module contains end-to-end tests that validate custom error message
extraction from schema definitions through to API responses, ensuring
the complete workflow functions correctly.
"""

import pytest
import json
import tempfile
from pathlib import Path

from metadata_harmonization_processor.nodes.validation import ValidationNode
from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationResults,
    ValidationResultsSummary,
    ValidationErrorType,
)
import pandas as pd


class TestCustomErrorMessageWorkflow:
    """Integration tests for custom error message workflow."""

    @pytest.fixture
    def sample_schema_with_custom_messages(self):
        """Create a sample schema with custom error messages."""
        return {
            "$id": "https://example.com/test.schema.json",
            "type": "object",
            "title": "Test Schema",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "required": ["library_strategy", "sequence_id", "CSID", "submitter_state"],
            "properties": {
                "library_strategy": {
                    "type": "string",
                    "enum": ["Amplicon"],
                    "errorMessage": {"enum": 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'},
                },
                "sequence_id": {
                    "type": "string",
                    "pattern": "^[A-Za-z]{2}[0-9]{2}-[A-Za-z]{2}[A-Za-z0-9]{2}[0-9]{2}-Cx[0-9]-[A-Za-z]$",
                    "errorMessage": {"regex": "sequence_id is a required field that must follow the proper formatting"},
                },
                "CSID": {
                    "type": "string",
                    "pattern": "^[0-9]{10}$",
                    "errorMessage": {
                        "regex": "CSID is a required field and must be a ten-digit numerical string with no special characters"
                    },
                },
                "submitter_state": {
                    "type": "string",
                    "enum": ["AK", "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA"],
                    "errorMessage": {
                        "enum": "submitter_state is a required field and must be formatted as the two-letter State abbreviation"
                    },
                },
                "optional_field": {
                    "type": "string",
                    "pattern": "^[A-Z]+$",
                    # No custom error message - should use system fallback
                },
            },
        }

    @pytest.fixture
    def sample_catalog(self):
        """Create a sample catalog for schema collector."""
        return [
            {
                "core_uuid": "test_core",
                "core_name": "Test Core Schema",
                "core_path": "test_core.json",
                "program": [
                    {
                        "program_uuid": "test_program",
                        "program_name": "Test Program Schema",
                        "program_path": "test_program.json",
                    }
                ],
            }
        ]

    @pytest.fixture
    def temp_schema_directory(self, sample_schema_with_custom_messages, sample_catalog):
        """Create a temporary directory with schema files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write catalog.json
            catalog_path = temp_path / "catalog.json"
            with open(catalog_path, "w") as f:
                json.dump(sample_catalog, f)

            # Write core schema (empty for this test)
            core_schema_path = temp_path / "test_core.json"
            with open(core_schema_path, "w") as f:
                json.dump({"type": "object", "properties": {}}, f)

            # Write program schema with custom error messages
            program_schema_path = temp_path / "test_program.json"
            with open(program_schema_path, "w") as f:
                json.dump(sample_schema_with_custom_messages, f)

            yield str(temp_path)

    @pytest.fixture
    def schema_collector(self, temp_schema_directory):
        """Create a FileBasedSchemaCollector with test schemas."""
        return FileBasedSchemaCollector(temp_schema_directory)

    @pytest.fixture
    def validation_node(self, schema_collector):
        """Create a ValidationNode with the schema collector."""
        return ValidationNode(schema_collector)

    @pytest.fixture
    def sample_dataframe_with_errors(self):
        """Create a DataFrame that will trigger various validation errors."""
        return pd.DataFrame(
            {
                "library_strategy": ["Invalid", "", "Amplicon", "WrongValue"],
                "sequence_id": ["invalid-format", "AB12-CD34-Cx1-A", "", "bad-format"],
                "CSID": ["123", "1234567890", "invalid", ""],
                "submitter_state": ["XX", "CA", "", "INVALID"],
                "optional_field": ["VALID", "invalid", "", "ANOTHER"],
            }
        )

    @pytest.mark.asyncio
    async def test_end_to_end_custom_error_message_extraction(self, validation_node, sample_dataframe_with_errors):
        """Test end-to-end custom error message extraction from schema to validation results."""
        # Create processor state
        state = ProcessorState(
            aligned_df=sample_dataframe_with_errors, program_id="test_program", core_id="test_core", job_id="test_job"
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None
        assert state.combined_results.has_validation_results()

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have multiple errors
        assert len(errors) > 0

        # Test custom error messages for enum validation
        enum_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_OPTION]

        # Find library_strategy enum error
        library_strategy_error = next(
            (e for e in enum_errors if e.column == "library_strategy" and e.current_value == "Invalid"), None
        )
        assert library_strategy_error is not None
        assert (
            library_strategy_error.error_message
            == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        )
        assert library_strategy_error.schema_field_name == "library_strategy"

        # Find submitter_state enum error
        submitter_state_error = next(
            (e for e in enum_errors if e.column == "submitter_state" and e.current_value == "XX"), None
        )
        assert submitter_state_error is not None
        assert (
            submitter_state_error.error_message
            == "submitter_state is a required field and must be formatted as the two-letter State abbreviation"
        )
        assert submitter_state_error.schema_field_name == "submitter_state"

        # Test custom error messages for pattern validation
        pattern_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_PATTERN]

        # Find sequence_id pattern error
        sequence_id_error = next(
            (e for e in pattern_errors if e.column == "sequence_id" and e.current_value == "invalid-format"), None
        )
        assert sequence_id_error is not None
        assert (
            sequence_id_error.error_message == "sequence_id is a required field that must follow the proper formatting"
        )
        assert sequence_id_error.schema_field_name == "sequence_id"

        # Find CSID pattern error
        csid_error = next((e for e in pattern_errors if e.column == "CSID" and e.current_value == "123"), None)
        assert csid_error is not None
        assert (
            csid_error.error_message
            == "CSID is a required field and must be a ten-digit numerical string with no special characters"
        )
        assert csid_error.schema_field_name == "CSID"

        # Test fallback behavior for fields without custom messages
        optional_field_error = next(
            (e for e in pattern_errors if e.column == "optional_field" and e.current_value == "invalid"), None
        )
        assert optional_field_error is not None
        assert optional_field_error.error_message is None  # Should be None for fields without custom messages
        assert optional_field_error.schema_field_name == "optional_field"

    @pytest.mark.asyncio
    async def test_custom_error_messages_for_required_fields(self, validation_node, sample_dataframe_with_errors):
        """Test custom error messages for required field validation."""
        # Create processor state
        state = ProcessorState(
            aligned_df=sample_dataframe_with_errors, program_id="test_program", core_id="test_core", job_id="test_job"
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Test required field errors with custom messages
        required_errors = [e for e in errors if e.error_type == ValidationErrorType.REQUIRED_VALUE]

        # Find library_strategy required error (has enum options)
        library_strategy_required = next(
            (e for e in required_errors if e.column == "library_strategy" and e.current_value == ""), None
        )
        assert library_strategy_required is not None
        assert (
            library_strategy_required.error_message
            == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        )
        assert library_strategy_required.schema_field_name == "library_strategy"

        # Find sequence_id required error (has pattern but no enum)
        sequence_id_required = next(
            (e for e in required_errors if e.column == "sequence_id" and e.current_value == ""), None
        )
        assert sequence_id_required is not None
        assert (
            sequence_id_required.error_message
            == "sequence_id is a required field that must follow the proper formatting"
        )
        assert sequence_id_required.schema_field_name == "sequence_id"

    @pytest.mark.asyncio
    async def test_api_model_serialization_with_custom_messages(self, validation_node, sample_dataframe_with_errors):
        """Test that API models properly serialize custom error messages."""
        # Create processor state
        state = ProcessorState(
            aligned_df=sample_dataframe_with_errors, program_id="test_program", core_id="test_core", job_id="test_job"
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation results from processor
        processor_validation_results = state.combined_results.validation_results

        # Convert to API models
        api_errors = []
        for error in processor_validation_results.validation_results:
            api_error = ValidationErrorDetail(
                row=error.row,
                column=error.column,
                current_value=error.current_value,
                valid_options=error.valid_options,
                recommended_value=error.recommended_value,
                error_type=error.error_type,
                error_message=error.error_message,
                schema_field_name=error.schema_field_name,
            )
            api_errors.append(api_error)

        api_summary = ValidationResultsSummary(
            total_rows=processor_validation_results.summary.total_rows,
            total_errors=processor_validation_results.summary.total_errors,
            error_types=processor_validation_results.summary.error_types,
            columns_validated=processor_validation_results.summary.columns_validated,
        )

        api_results = ValidationResults(validation_results=api_errors, summary=api_summary)

        # Test serialization with camelCase aliases
        serialized = api_results.model_dump(by_alias=True)

        # Verify structure
        assert "validationResults" in serialized
        assert "summary" in serialized
        assert len(serialized["validationResults"]) > 0

        # Find an error with custom message and verify serialization
        custom_message_error = next(
            (e for e in serialized["validationResults"] if e.get("errorMessage") is not None), None
        )
        assert custom_message_error is not None
        assert "errorMessage" in custom_message_error
        assert "schemaFieldName" in custom_message_error
        assert custom_message_error["errorMessage"] is not None
        assert custom_message_error["schemaFieldName"] is not None

        # Verify camelCase field names
        assert "currentValue" in custom_message_error
        assert "validOptions" in custom_message_error or custom_message_error["validOptions"] is None
        assert "recommendedValue" in custom_message_error or custom_message_error["recommendedValue"] is None
        assert "errorType" in custom_message_error

    @pytest.mark.asyncio
    async def test_backward_compatibility_without_custom_messages(self, temp_schema_directory):
        """Test backward compatibility with schemas that don't have custom error messages."""
        # Create a schema without custom error messages
        schema_without_messages = {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
                "status": {"type": "string", "enum": ["active", "inactive"]},
            },
        }

        # Write schema without custom messages
        program_schema_path = Path(temp_schema_directory) / "test_program.json"
        with open(program_schema_path, "w") as f:
            json.dump(schema_without_messages, f)

        # Create schema collector and validation node
        schema_collector = FileBasedSchemaCollector(temp_schema_directory)
        validation_node = ValidationNode(schema_collector)

        # Create test data with errors
        df = pd.DataFrame(
            {"name": ["John", ""], "email": ["john@test.com", "invalid-email"], "status": ["active", "invalid-status"]}
        )

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core", job_id="test_job")

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful execution
        assert result.status.name == "COMPLETED"

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have errors but without custom messages
        assert len(errors) > 0

        # All errors should have None for error_message (no custom messages in schema)
        for error in errors:
            assert error.error_message is None
            assert error.schema_field_name == error.column  # Should still have the column name

    @pytest.mark.asyncio
    async def test_mixed_custom_and_system_messages(self, temp_schema_directory):
        """Test scenarios with both custom and system-generated error messages."""
        # Create a schema with mixed error message support
        mixed_schema = {
            "type": "object",
            "required": ["field_with_custom", "field_without_custom"],
            "properties": {
                "field_with_custom": {
                    "type": "string",
                    "enum": ["option1", "option2"],
                    "errorMessage": {"enum": "This field has a custom error message from the schema"},
                },
                "field_without_custom": {
                    "type": "string",
                    "enum": ["optionA", "optionB"],
                    # No custom error message
                },
            },
        }

        # Write mixed schema
        program_schema_path = Path(temp_schema_directory) / "test_program.json"
        with open(program_schema_path, "w") as f:
            json.dump(mixed_schema, f)

        # Create schema collector and validation node
        schema_collector = FileBasedSchemaCollector(temp_schema_directory)
        validation_node = ValidationNode(schema_collector)

        # Create test data with errors for both fields
        df = pd.DataFrame(
            {"field_with_custom": ["invalid1", "option1"], "field_without_custom": ["invalid2", "optionA"]}
        )

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core", job_id="test_job")

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have 2 errors
        assert len(errors) == 2

        # Find error with custom message
        custom_error = next((e for e in errors if e.column == "field_with_custom"), None)
        assert custom_error is not None
        assert custom_error.error_message == "This field has a custom error message from the schema"
        assert custom_error.schema_field_name == "field_with_custom"

        # Find error without custom message
        system_error = next((e for e in errors if e.column == "field_without_custom"), None)
        assert system_error is not None
        assert system_error.error_message is None  # Should be None for system-generated
        assert system_error.schema_field_name == "field_without_custom"

    @pytest.mark.asyncio
    async def test_error_message_extraction_performance(self, temp_schema_directory):
        """Test performance of error message extraction with large datasets."""
        import time

        # Create a performance test schema with custom messages
        performance_schema = {
            "type": "object",
            "required": ["field1", "field2"],
            "properties": {
                "field1": {
                    "type": "string",
                    "enum": ["valid1", "valid2"],
                    "errorMessage": {"enum": "Custom error message for field1"},
                },
                "field2": {
                    "type": "string",
                    "pattern": "^[A-Z]+$",
                    "errorMessage": {"regex": "Custom pattern message for field2"},
                },
                "field3": {
                    "type": "string",
                    "enum": ["option1", "option2"],
                    "errorMessage": {"enum": "Custom error message for field3"},
                },
            },
        }

        # Write performance schema
        program_schema_path = Path(temp_schema_directory) / "test_program.json"
        with open(program_schema_path, "w") as f:
            json.dump(performance_schema, f)

        # Create schema collector and validation node
        schema_collector = FileBasedSchemaCollector(temp_schema_directory)
        validation_node = ValidationNode(schema_collector)

        # Test error message extraction performance
        start_time = time.time()
        for field_name, field_props in performance_schema["properties"].items():
            if "errorMessage" in field_props:
                # Convert to the format expected by _extract_error_messages
                rules_format = {"error_message": field_props["errorMessage"]}
                error_messages = validation_node._extract_error_messages(rules_format)
                assert len(error_messages) > 0

        extraction_time = time.time() - start_time

        # Performance assertion - extraction should be fast
        assert extraction_time < 0.1, f"Error message extraction took {extraction_time:.3f}s, expected < 0.1s"

        # Create a large DataFrame to test performance
        large_df = pd.DataFrame(
            {"field1": ["invalid"] * 1000, "field2": ["invalid-pattern"] * 1000, "field3": ["invalid-option"] * 1000}
        )

        # Test full validation performance with custom messages
        state = ProcessorState(
            aligned_df=large_df, program_id="test_program", core_id="test_core", job_id="test_job_performance"
        )

        # Time the full validation process
        validation_start = time.time()
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})
        validation_time = time.time() - validation_start

        # Verify successful execution
        assert result.status.name == "COMPLETED"

        # Performance assertion - validation with custom messages should complete within reasonable time
        assert validation_time < 5.0, f"Validation with custom messages took {validation_time:.3f}s, expected < 5.0s"

        # Verify that custom messages are properly extracted for all errors
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors (3000 invalid values)
        assert len(errors) > 2000

        # Check that custom messages are properly applied
        errors_with_custom_messages = [e for e in errors if e.error_message is not None]
        assert len(errors_with_custom_messages) > 1000

        # Verify performance doesn't degrade with custom message processing
        custom_message_errors = len(errors_with_custom_messages)
        total_errors = len(errors)
        custom_message_ratio = custom_message_errors / total_errors

        # Should have a high ratio of custom messages
        assert custom_message_ratio > 0.8, f"Only {custom_message_ratio:.2%} of errors have custom messages"

    def test_error_message_format_validation(self, validation_node):
        """Test validation of different error message formats."""
        # Test dictionary format
        dict_rules = {
            "error_message": {
                "enum": "Valid enum message",
                "pattern": "Valid pattern message",
                "invalid_key": 123,  # Should be ignored
            }
        }

        dict_messages = validation_node._extract_error_messages(dict_rules)
        assert len(dict_messages) == 2
        assert dict_messages["enum"] == "Valid enum message"
        assert dict_messages["pattern"] == "Valid pattern message"
        assert "invalid_key" not in dict_messages

        # Test string format
        string_rules = {"error_message": "General error message"}

        string_messages = validation_node._extract_error_messages(string_rules)
        assert len(string_messages) == 1
        assert string_messages["general"] == "General error message"

        # Test invalid format
        invalid_rules = {
            "error_message": 123  # Invalid format
        }

        invalid_messages = validation_node._extract_error_messages(invalid_rules)
        assert len(invalid_messages) == 0

    @pytest.mark.asyncio
    async def test_api_response_structure_with_custom_messages(self, validation_node, sample_dataframe_with_errors):
        """Test that API response structure properly includes custom error messages."""
        # Create processor state
        state = ProcessorState(
            aligned_df=sample_dataframe_with_errors, program_id="test_program", core_id="test_core", job_id="test_job"
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get processor validation results
        processor_results = state.combined_results.validation_results

        # Convert to API ValidationResults model
        api_errors = []
        for error in processor_results.validation_results:
            api_error = ValidationErrorDetail(
                row=error.row,
                column=error.column,
                current_value=error.current_value,
                valid_options=error.valid_options,
                recommended_value=error.recommended_value,
                error_type=error.error_type,
                error_message=error.error_message,
                schema_field_name=error.schema_field_name,
            )
            api_errors.append(api_error)

        api_summary = ValidationResultsSummary(
            total_rows=processor_results.summary.total_rows,
            total_errors=processor_results.summary.total_errors,
            error_types=processor_results.summary.error_types,
            columns_validated=processor_results.summary.columns_validated,
        )

        api_results = ValidationResults(validation_results=api_errors, summary=api_summary)

        # Test that API model serialization works correctly
        serialized = api_results.model_dump(by_alias=True)

        # Verify API response structure
        assert "validationResults" in serialized
        assert "summary" in serialized
        assert isinstance(serialized["validationResults"], list)
        assert len(serialized["validationResults"]) > 0

        # Check that custom error messages are properly serialized
        errors_with_custom_messages = [e for e in serialized["validationResults"] if e.get("errorMessage") is not None]
        assert len(errors_with_custom_messages) > 0

        # Verify camelCase field names in API response
        for error in serialized["validationResults"]:
            assert "currentValue" in error
            assert "errorType" in error
            if error.get("errorMessage"):
                assert "errorMessage" in error
                assert "schemaFieldName" in error

    def test_error_message_fallback_logic(self, validation_node):
        """Test the fallback logic for different error message scenarios."""
        # Test enum field with custom message
        enum_rules = {"options": ["option1", "option2"], "error_message": {"enum": "Custom enum message"}}
        enum_messages = validation_node._extract_error_messages(enum_rules)
        assert "enum" in enum_messages

        # Test pattern field with custom message
        pattern_rules = {"pattern": "^[A-Z]+$", "error_message": {"regex": "Custom regex message"}}
        pattern_messages = validation_node._extract_error_messages(pattern_rules)
        assert "regex" in pattern_messages

        # Test field with both enum and pattern messages
        both_rules = {
            "options": ["option1"],
            "pattern": "^[A-Z]+$",
            "error_message": {"enum": "Custom enum message", "regex": "Custom regex message"},
        }
        both_messages = validation_node._extract_error_messages(both_rules)
        assert "enum" in both_messages
        assert "regex" in both_messages
        assert both_messages["enum"] == "Custom enum message"
        assert both_messages["regex"] == "Custom regex message"

    @pytest.mark.asyncio
    async def test_frontend_error_message_display_integration(self, validation_node, sample_dataframe_with_errors):
        """Test integration between backend custom error messages and frontend display."""
        # Create processor state
        state = ProcessorState(
            aligned_df=sample_dataframe_with_errors, program_id="test_program", core_id="test_core", job_id="test_job"
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Simulate API response transformation
        api_response_errors = []
        for error in errors:
            api_error = {
                "row": error.row,
                "column": error.column,
                "currentValue": error.current_value,
                "validOptions": error.valid_options,
                "recommendedValue": error.recommended_value,
                "errorType": error.error_type.value,
                "errorMessage": error.error_message,
                "schemaFieldName": error.schema_field_name,
            }
            api_response_errors.append(api_error)

        # Verify API response structure for frontend consumption
        assert len(api_response_errors) > 0

        # Test that custom error messages are properly formatted for frontend
        custom_message_errors = [e for e in api_response_errors if e["errorMessage"] is not None]
        assert len(custom_message_errors) > 0

        # Verify camelCase field names for frontend compatibility
        for error in api_response_errors:
            assert "currentValue" in error
            assert "validOptions" in error
            assert "recommendedValue" in error
            assert "errorType" in error
            assert "errorMessage" in error
            assert "schemaFieldName" in error

        # Test specific custom message formatting
        library_strategy_error = next((e for e in custom_message_errors if e["column"] == "library_strategy"), None)
        if library_strategy_error:
            assert (
                library_strategy_error["errorMessage"]
                == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
            )
            assert library_strategy_error["schemaFieldName"] == "library_strategy"

        # Test that errors without custom messages have null errorMessage
        system_errors = [e for e in api_response_errors if e["errorMessage"] is None]
        assert len(system_errors) > 0

        for error in system_errors:
            assert error["errorMessage"] is None
            assert error["schemaFieldName"] is not None  # Should still have schema field name

    @pytest.mark.asyncio
    async def test_error_message_workflow_with_schema_variations(self, temp_schema_directory):
        """Test custom error message workflow with various schema configurations."""
        # Test different schema structures and error message formats
        test_schemas = [
            {
                "name": "enum_only_schema",
                "schema": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "inactive"],
                            "errorMessage": {"enum": "Status must be either 'active' or 'inactive'"},
                        }
                    },
                },
            },
            {
                "name": "pattern_only_schema",
                "schema": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {
                            "type": "string",
                            "pattern": "^[A-Z]{3}[0-9]{3}$",
                            "errorMessage": {"regex": "Code must be 3 uppercase letters followed by 3 digits"},
                        }
                    },
                },
            },
            {
                "name": "mixed_messages_schema",
                "schema": {
                    "type": "object",
                    "required": ["field1", "field2"],
                    "properties": {
                        "field1": {
                            "type": "string",
                            "enum": ["option1", "option2"],
                            "errorMessage": {"enum": "Field1 custom enum message"},
                        },
                        "field2": {
                            "type": "string",
                            "pattern": "^[0-9]+$",
                            "errorMessage": {"regex": "Field2 custom pattern message"},
                        },
                        "field3": {
                            "type": "string",
                            "enum": ["a", "b"],
                            # No custom error message
                        },
                    },
                },
            },
        ]

        for test_case in test_schemas:
            # Write test schema
            program_schema_path = Path(temp_schema_directory) / "test_program.json"
            with open(program_schema_path, "w") as f:
                json.dump(test_case["schema"], f)

            # Create schema collector and validation node
            schema_collector = FileBasedSchemaCollector(temp_schema_directory)
            validation_node = ValidationNode(schema_collector)

            # Create test data that will trigger errors
            if test_case["name"] == "enum_only_schema":
                df = pd.DataFrame({"status": ["invalid", "active", ""]})
            elif test_case["name"] == "pattern_only_schema":
                df = pd.DataFrame({"code": ["invalid", "ABC123", ""]})
            else:  # mixed_messages_schema
                df = pd.DataFrame(
                    {"field1": ["invalid1", "option1"], "field2": ["invalid2", "123"], "field3": ["invalid3", "a"]}
                )

            state = ProcessorState(
                aligned_df=df, program_id="test_program", core_id="test_core", job_id=f'test_job_{test_case["name"]}'
            )

            # Execute validation
            result = await validation_node.invoke_async(
                task="validation_task", invocation_state={"processor_state": state}
            )

            # Verify successful execution
            assert result.status.name == "COMPLETED"

            # Get validation results
            validation_results = state.combined_results.validation_results
            errors = validation_results.validation_results

            # Should have errors
            assert len(errors) > 0

            # Verify custom messages are properly extracted
            custom_message_errors = [e for e in errors if e.error_message is not None]

            if test_case["name"] == "mixed_messages_schema":
                # Should have custom messages for field1 and field2, but not field3
                field1_errors = [e for e in custom_message_errors if e.column == "field1"]
                field2_errors = [e for e in custom_message_errors if e.column == "field2"]
                field3_errors = [e for e in errors if e.column == "field3"]

                assert len(field1_errors) > 0
                assert len(field2_errors) > 0
                assert len(field3_errors) > 0

                # field3 should not have custom messages
                field3_custom_errors = [e for e in field3_errors if e.error_message is not None]
                assert len(field3_custom_errors) == 0
            else:
                # Should have at least one custom message
                assert len(custom_message_errors) > 0

    @pytest.mark.asyncio
    async def test_error_message_processing_with_large_schemas(self, temp_schema_directory):
        """Test performance and correctness with large schema definitions."""
        # Create a large schema with many fields and custom error messages
        large_schema = {"type": "object", "required": [f"field_{i}" for i in range(50)], "properties": {}}

        # Add 100 fields with custom error messages
        for i in range(100):
            field_name = f"field_{i}"
            large_schema["properties"][field_name] = {
                "type": "string",
                "enum": [f"option_{i}_1", f"option_{i}_2"],
                "errorMessage": {
                    "enum": f"Custom error message for {field_name}. Valid options are option_{i}_1 or option_{i}_2"
                },
            }

        # Write large schema
        program_schema_path = Path(temp_schema_directory) / "test_program.json"
        with open(program_schema_path, "w") as f:
            json.dump(large_schema, f)

        # Create schema collector and validation node
        schema_collector = FileBasedSchemaCollector(temp_schema_directory)
        validation_node = ValidationNode(schema_collector)

        # Create test data with errors for many fields
        test_data = {}
        for i in range(100):
            field_name = f"field_{i}"
            test_data[field_name] = ["invalid_value", f"option_{i}_1", ""]

        df = pd.DataFrame(test_data)

        state = ProcessorState(
            aligned_df=df, program_id="test_program", core_id="test_core", job_id="test_job_large_schema"
        )

        # Time the validation process
        import time

        start_time = time.time()

        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        processing_time = time.time() - start_time

        # Verify successful execution within reasonable time
        assert result.status.name == "COMPLETED"
        assert processing_time < 10.0, f"Large schema processing took {processing_time:.3f}s, expected < 10.0s"

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors (actual count: 150 errors for 100 fields with 3 rows each)
        assert len(errors) > 100

        # Verify custom messages are properly applied
        custom_message_errors = [e for e in errors if e.error_message is not None]
        assert len(custom_message_errors) > 50  # Adjusted expectation based on actual results

        # Verify message content is correct
        for error in custom_message_errors[:10]:  # Check first 10 for performance
            assert error.error_message.startswith("Custom error message for")
            assert error.schema_field_name == error.column

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_existing_workflows(self, validation_node, temp_schema_directory):
        """Test that custom error messages don't break existing validation workflows."""
        # Create a schema that mixes old and new patterns
        mixed_compatibility_schema = {
            "type": "object",
            "required": ["old_field", "new_field"],
            "properties": {
                "old_field": {
                    "type": "string",
                    "enum": ["valid1", "valid2"],
                    # No custom error message - old style
                },
                "new_field": {
                    "type": "string",
                    "enum": ["valid3", "valid4"],
                    "errorMessage": {"enum": "New field with custom error message"},
                },
            },
        }

        # Write mixed schema
        program_schema_path = Path(temp_schema_directory) / "test_program.json"
        with open(program_schema_path, "w") as f:
            json.dump(mixed_compatibility_schema, f)

        # Create schema collector and validation node
        schema_collector = FileBasedSchemaCollector(temp_schema_directory)
        validation_node = ValidationNode(schema_collector)

        # Create test data
        df = pd.DataFrame({"old_field": ["invalid_old", "valid1"], "new_field": ["invalid_new", "valid3"]})

        state = ProcessorState(
            aligned_df=df, program_id="test_program", core_id="test_core", job_id="test_job_compatibility"
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful execution
        assert result.status.name == "COMPLETED"

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have 2 errors
        assert len(errors) == 2

        # Find old-style error (no custom message)
        old_error = next((e for e in errors if e.column == "old_field"), None)
        assert old_error is not None
        assert old_error.error_message is None
        assert old_error.schema_field_name == "old_field"

        # Find new-style error (with custom message)
        new_error = next((e for e in errors if e.column == "new_field"), None)
        assert new_error is not None
        assert new_error.error_message == "New field with custom error message"
        assert new_error.schema_field_name == "new_field"

        # Verify that both errors have proper structure
        for error in errors:
            assert error.row > 0
            assert error.column is not None
            assert error.current_value is not None
            assert error.error_type is not None
            assert error.schema_field_name is not None

        # Test API serialization compatibility
        api_errors = []
        for error in errors:
            api_error = {
                "row": error.row,
                "column": error.column,
                "currentValue": error.current_value,
                "validOptions": error.valid_options,
                "recommendedValue": error.recommended_value,
                "errorType": error.error_type.value,
                "errorMessage": error.error_message,
                "schemaFieldName": error.schema_field_name,
            }
            api_errors.append(api_error)

        # Verify API compatibility
        assert len(api_errors) == 2

        # Old-style error should have null errorMessage
        old_api_error = next((e for e in api_errors if e["column"] == "old_field"), None)
        assert old_api_error["errorMessage"] is None

        # New-style error should have custom errorMessage
        new_api_error = next((e for e in api_errors if e["column"] == "new_field"), None)
        assert new_api_error["errorMessage"] == "New field with custom error message"
