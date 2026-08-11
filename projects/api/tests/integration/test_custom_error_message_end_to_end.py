# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
End-to-end integration tests for custom error message workflow.

This module contains comprehensive integration tests that validate the complete
custom error message workflow from schema definition through API processing
to frontend display, ensuring all components work together correctly.
"""

import pytest
import json
import tempfile
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from metadata_harmonization_processor.nodes.validation import ValidationNode
from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_api.api.v1.models.metadata import (
    ValidationStatusResponse,
    CombinedResults as APICombinedResults,
)
import pandas as pd


class TestCustomErrorMessageEndToEnd:
    """End-to-end integration tests for custom error message workflow."""

    @pytest.fixture
    def comprehensive_schema_with_custom_messages(self):
        """Create a comprehensive schema with various custom error message types."""
        return {
            "$id": "https://example.com/comprehensive.schema.json",
            "type": "object",
            "title": "Comprehensive Test Schema",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "required": [
                "enum_field_with_custom",
                "pattern_field_with_custom",
                "required_field_with_custom",
                "enum_field_without_custom",
                "pattern_field_without_custom",
            ],
            "properties": {
                "enum_field_with_custom": {
                    "type": "string",
                    "enum": ["option1", "option2", "option3"],
                    "errorMessage": {
                        "enum": "enum_field_with_custom must be one of the following: option1, option2, or option3. Please check your data and select a valid option."
                    },
                },
                "pattern_field_with_custom": {
                    "type": "string",
                    "pattern": "^[A-Z]{2}[0-9]{4}$",
                    "errorMessage": {
                        "regex": "pattern_field_with_custom must follow the format: two uppercase letters followed by four digits (e.g., AB1234). Please correct the formatting."
                    },
                },
                "required_field_with_custom": {
                    "type": "string",
                    "minLength": 1,
                    "errorMessage": {
                        "general": "required_field_with_custom is mandatory and cannot be empty. Please provide a valid value."
                    },
                },
                "enum_field_without_custom": {
                    "type": "string",
                    "enum": ["valueA", "valueB", "valueC"],
                    # No custom error message - should use system fallback
                },
                "pattern_field_without_custom": {
                    "type": "string",
                    "pattern": "^[0-9]{3}-[0-9]{3}-[0-9]{4}$",
                    # No custom error message - should use system fallback
                },
                "optional_field": {
                    "type": "string",
                    "enum": ["yes", "no"],
                    "errorMessage": {"enum": "optional_field should be either 'yes' or 'no' if provided."},
                },
            },
        }

    @pytest.fixture
    def sample_catalog(self):
        """Create a sample catalog for schema collector."""
        return [
            {
                "core_uuid": "comprehensive_core",
                "core_name": "Comprehensive Core Schema",
                "core_path": "comprehensive_core.json",
                "program": [
                    {
                        "program_uuid": "comprehensive_program",
                        "program_name": "Comprehensive Program Schema",
                        "program_path": "comprehensive_program.json",
                    }
                ],
            }
        ]

    @pytest.fixture
    def temp_schema_directory(self, comprehensive_schema_with_custom_messages, sample_catalog):
        """Create a temporary directory with comprehensive schema files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write catalog.json
            catalog_path = temp_path / "catalog.json"
            with open(catalog_path, "w") as f:
                json.dump(sample_catalog, f)

            # Write core schema (empty for this test)
            core_schema_path = temp_path / "comprehensive_core.json"
            with open(core_schema_path, "w") as f:
                json.dump({"type": "object", "properties": {}}, f)

            # Write program schema with comprehensive custom error messages
            program_schema_path = temp_path / "comprehensive_program.json"
            with open(program_schema_path, "w") as f:
                json.dump(comprehensive_schema_with_custom_messages, f)

            yield str(temp_path)

    @pytest.fixture
    def schema_collector(self, temp_schema_directory):
        """Create a FileBasedSchemaCollector with comprehensive test schemas."""
        return FileBasedSchemaCollector(temp_schema_directory)

    @pytest.fixture
    def validation_node(self, schema_collector):
        """Create a ValidationNode with the schema collector."""
        return ValidationNode(schema_collector)

    @pytest.fixture
    def comprehensive_test_dataframe(self):
        """Create a comprehensive DataFrame that triggers various validation errors."""
        return pd.DataFrame(
            {
                "enum_field_with_custom": ["invalid_enum", "option1", "", "wrong_option", "option2"],
                "pattern_field_with_custom": ["invalid", "AB1234", "", "ab1234", "XY9999"],
                "required_field_with_custom": ["valid", "", "another_valid", "test", ""],
                "enum_field_without_custom": ["invalid_enum", "valueA", "", "wrong_value", "valueB"],
                "pattern_field_without_custom": ["invalid", "123-456-7890", "", "123-45-6789", "987-654-3210"],
                "optional_field": ["invalid", "yes", "", "maybe", "no"],
            }
        )

    @pytest.mark.asyncio
    async def test_complete_end_to_end_workflow(self, validation_node, comprehensive_test_dataframe):
        """Test the complete end-to-end custom error message workflow."""
        # Step 1: Process validation with custom error messages
        state = ProcessorState(
            aligned_df=comprehensive_test_dataframe,
            program_id="comprehensive_program",
            core_id="comprehensive_core",
            job_id="end_to_end_test_job",
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None
        assert state.combined_results.has_validation_results()

        # Step 2: Extract processor validation results
        processor_validation_results = state.combined_results.validation_results
        processor_errors = processor_validation_results.validation_results

        # Verify we have errors with custom messages
        assert len(processor_errors) > 0

        # Step 3: Convert to API models (simulating API layer)
        api_errors = []
        for error in processor_errors:
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

        # Step 4: Test API response serialization
        from uuid import uuid4

        api_response = ValidationStatusResponse(
            job_id=uuid4(),
            user_id="test_user",
            core_schema_id="comprehensive_core",
            program_schema_id="comprehensive_program",
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
            current_version=1,
            latest_results=APICombinedResults(validation_results=api_results, schema_alignment_results=None),
        )

        # Serialize to JSON (simulating API response)
        serialized_response = api_response.model_dump(by_alias=True)

        # Step 5: Verify end-to-end data integrity
        assert "jobId" in serialized_response
        assert "latestResults" in serialized_response
        assert "validationResults" in serialized_response["latestResults"]

        validation_results_wrapper = serialized_response["latestResults"]["validationResults"]
        assert "validationResults" in validation_results_wrapper
        validation_errors = validation_results_wrapper["validationResults"]
        assert len(validation_errors) > 0

        # Step 6: Verify custom error messages are preserved through the entire workflow
        custom_message_errors = [e for e in validation_errors if e.get("errorMessage") is not None]
        assert len(custom_message_errors) > 0

        # Verify specific custom messages
        enum_custom_error = next(
            (
                e
                for e in custom_message_errors
                if e.get("column") == "enum_field_with_custom"
                and "option1, option2, or option3" in e.get("errorMessage", "")
            ),
            None,
        )
        assert enum_custom_error is not None
        assert "Please check your data and select a valid option" in enum_custom_error["errorMessage"]

        pattern_custom_error = next(
            (
                e
                for e in custom_message_errors
                if e.get("column") == "pattern_field_with_custom"
                and "two uppercase letters followed by four digits" in e.get("errorMessage", "")
            ),
            None,
        )
        assert pattern_custom_error is not None
        assert "Please correct the formatting" in pattern_custom_error["errorMessage"]

        # Step 7: Verify fallback behavior for fields without custom messages
        system_generated_errors = [
            e
            for e in validation_errors
            if e.get("errorMessage") is None
            and e.get("column") in ["enum_field_without_custom", "pattern_field_without_custom"]
        ]
        assert len(system_generated_errors) > 0

        # Step 8: Verify schema field name context is preserved
        for error in validation_errors:
            assert "schemaFieldName" in error
            assert error["schemaFieldName"] is not None

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset_and_custom_messages(self, validation_node):
        """Test performance of custom error message processing with large datasets."""
        # Create a large dataset with many validation errors
        large_size = 1000
        large_df = pd.DataFrame(
            {
                "enum_field_with_custom": ["invalid_value"] * large_size,
                "pattern_field_with_custom": ["invalid_pattern"] * large_size,
                "required_field_with_custom": [""] * large_size,  # Empty values
                "enum_field_without_custom": ["invalid_enum"] * large_size,
                "pattern_field_without_custom": ["invalid_pattern"] * large_size,
                "optional_field": ["invalid_optional"] * large_size,
            }
        )

        state = ProcessorState(
            aligned_df=large_df,
            program_id="comprehensive_program",
            core_id="comprehensive_core",
            job_id="performance_test_job",
        )

        # Measure processing time
        start_time = time.time()

        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        processing_time = time.time() - start_time

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None

        # Performance assertion - should complete within reasonable time
        assert processing_time < 10.0, f"Processing took {processing_time:.3f}s, expected < 10.0s"

        # Verify results quality
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors (6 errors per row * 1000 rows = up to 6000 errors)
        assert len(errors) > 3000

        # Verify custom messages are properly applied even with large datasets
        custom_message_errors = [e for e in errors if e.error_message is not None]
        system_message_errors = [e for e in errors if e.error_message is None]

        # Should have both custom and system-generated errors
        assert len(custom_message_errors) > 1000
        assert len(system_message_errors) > 1000

        # Measure API conversion performance
        api_conversion_start = time.time()

        api_errors = []
        for error in errors:
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

        api_conversion_time = time.time() - api_conversion_start

        # API conversion should also be fast
        assert api_conversion_time < 2.0, f"API conversion took {api_conversion_time:.3f}s, expected < 2.0s"

        # Measure serialization performance
        serialization_start = time.time()

        api_results = ValidationResults(
            validation_results=api_errors,
            summary=ValidationResultsSummary(
                total_rows=validation_results.summary.total_rows,
                total_errors=validation_results.summary.total_errors,
                error_types=validation_results.summary.error_types,
                columns_validated=validation_results.summary.columns_validated,
            ),
        )

        serialized = api_results.model_dump(by_alias=True)

        serialization_time = time.time() - serialization_start

        # Serialization should be fast
        assert serialization_time < 1.0, f"Serialization took {serialization_time:.3f}s, expected < 1.0s"

        # Verify serialized data integrity
        assert len(serialized["validationResults"]) == len(errors)

        # Verify custom messages are preserved in serialization
        serialized_custom_errors = [e for e in serialized["validationResults"] if e.get("errorMessage") is not None]
        assert len(serialized_custom_errors) == len(custom_message_errors)

    @pytest.mark.asyncio
    async def test_error_message_formatting_and_display_integration(
        self, validation_node, comprehensive_test_dataframe
    ):
        """Test error message formatting and display integration across the workflow."""
        state = ProcessorState(
            aligned_df=comprehensive_test_dataframe,
            program_id="comprehensive_program",
            core_id="comprehensive_core",
            job_id="formatting_test_job",
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation results
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Test different error message formats
        custom_message_errors = [e for e in errors if e.error_message is not None]
        assert len(custom_message_errors) > 0

        # Test enum error message formatting
        enum_errors = [
            e
            for e in custom_message_errors
            if e.column == "enum_field_with_custom" and "option1, option2, or option3" in e.error_message
        ]
        assert len(enum_errors) > 0

        for error in enum_errors:
            # Verify message contains helpful information
            assert "must be one of the following" in error.error_message
            assert "Please check your data" in error.error_message
            assert error.schema_field_name == "enum_field_with_custom"

        # Test pattern error message formatting
        pattern_errors = [
            e
            for e in custom_message_errors
            if e.column == "pattern_field_with_custom"
            and "two uppercase letters followed by four digits" in e.error_message
        ]
        assert len(pattern_errors) > 0

        for error in pattern_errors:
            # Verify message contains format specification and example
            assert "AB1234" in error.error_message
            assert "Please correct the formatting" in error.error_message
            assert error.schema_field_name == "pattern_field_with_custom"

        # Test required field error message formatting
        required_errors = [
            e
            for e in custom_message_errors
            if e.column == "required_field_with_custom" and "mandatory and cannot be empty" in e.error_message
        ]
        assert len(required_errors) > 0

        for error in required_errors:
            # Verify message explains requirement clearly
            assert "Please provide a valid value" in error.error_message
            assert error.schema_field_name == "required_field_with_custom"

        # Convert to API format and test formatting preservation
        api_errors = []
        for error in errors:
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

        # Test that formatting is preserved in API serialization
        api_results = ValidationResults(
            validation_results=api_errors,
            summary=ValidationResultsSummary(
                total_rows=validation_results.summary.total_rows,
                total_errors=validation_results.summary.total_errors,
                error_types=validation_results.summary.error_types,
                columns_validated=validation_results.summary.columns_validated,
            ),
        )

        serialized = api_results.model_dump(by_alias=True)

        # Verify formatting is preserved in serialized output
        serialized_custom_errors = [e for e in serialized["validationResults"] if e.get("errorMessage") is not None]

        # Check that specific formatting elements are preserved
        enum_serialized = next(
            (e for e in serialized_custom_errors if "option1, option2, or option3" in e.get("errorMessage", "")), None
        )
        assert enum_serialized is not None
        assert "Please check your data" in enum_serialized["errorMessage"]

        pattern_serialized = next((e for e in serialized_custom_errors if "AB1234" in e.get("errorMessage", "")), None)
        assert pattern_serialized is not None
        assert "Please correct the formatting" in pattern_serialized["errorMessage"]

    def test_concurrent_validation_with_custom_messages(self, validation_node, comprehensive_test_dataframe):
        """Test concurrent validation processing with custom error messages."""

        async def run_validation(job_suffix: str):
            """Run a single validation job."""
            state = ProcessorState(
                aligned_df=comprehensive_test_dataframe.copy(),
                program_id="comprehensive_program",
                core_id="comprehensive_core",
                job_id=f"concurrent_test_job_{job_suffix}",
            )

            result = await validation_node.invoke_async(
                task="validation_task", invocation_state={"processor_state": state}
            )

            return state, result

        async def test_concurrent_execution():
            """Test multiple concurrent validations."""
            # Run multiple validations concurrently
            tasks = [run_validation(f"job_{i}") for i in range(5)]

            results = await asyncio.gather(*tasks)

            # Verify all validations completed successfully
            for state, result in results:
                assert result.status.name == "COMPLETED"
                assert state.combined_results is not None

                # Verify custom error messages are properly extracted
                validation_results = state.combined_results.validation_results
                errors = validation_results.validation_results

                custom_message_errors = [e for e in errors if e.error_message is not None]
                assert len(custom_message_errors) > 0

                # Verify specific custom messages are present
                enum_custom_errors = [e for e in custom_message_errors if e.column == "enum_field_with_custom"]
                assert len(enum_custom_errors) > 0

                for error in enum_custom_errors:
                    assert "option1, option2, or option3" in error.error_message

        # Run the concurrent test
        asyncio.run(test_concurrent_execution())

    @pytest.mark.asyncio
    async def test_memory_usage_with_custom_messages(self, validation_node):
        """Test memory usage when processing custom error messages."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create a moderately large dataset
        large_df = pd.DataFrame(
            {
                "enum_field_with_custom": ["invalid"] * 500,
                "pattern_field_with_custom": ["invalid"] * 500,
                "required_field_with_custom": [""] * 500,
                "enum_field_without_custom": ["invalid"] * 500,
                "pattern_field_without_custom": ["invalid"] * 500,
                "optional_field": ["invalid"] * 500,
            }
        )

        state = ProcessorState(
            aligned_df=large_df,
            program_id="comprehensive_program",
            core_id="comprehensive_core",
            job_id="memory_test_job",
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Check memory usage after processing
        post_processing_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = post_processing_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for this dataset)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, expected < 100MB"

        # Verify successful execution
        assert result.status.name == "COMPLETED"

        # Convert to API format (this can use additional memory)
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        api_errors = []
        for error in errors:
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

        # Check memory after API conversion
        post_api_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = post_api_memory - initial_memory

        # Total memory increase should still be reasonable
        assert total_memory_increase < 150, f"Total memory increased by {total_memory_increase:.2f}MB, expected < 150MB"

        # Verify data integrity
        assert len(api_errors) == len(errors)
        custom_message_count = len([e for e in api_errors if e.error_message is not None])
        assert custom_message_count > 0
