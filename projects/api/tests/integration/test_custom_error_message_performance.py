# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Performance tests for custom error message workflow.

This module contains performance-focused tests that validate the efficiency
and scalability of custom error message processing across different scenarios
and dataset sizes.
"""

import pytest
import json
import tempfile
import time
import asyncio
import psutil
import os
from pathlib import Path

from metadata_harmonization_processor.nodes.validation import ValidationNode
from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationResults,
    ValidationResultsSummary,
)
import pandas as pd


class TestCustomErrorMessagePerformance:
    """Performance tests for custom error message workflow."""

    @pytest.fixture
    def performance_schema_with_custom_messages(self):
        """Create a schema optimized for performance testing with various custom error message types."""
        return {
            "$id": "https://example.com/performance.schema.json",
            "type": "object",
            "title": "Performance Test Schema",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "required": [
                "enum_field_1",
                "enum_field_2",
                "enum_field_3",
                "pattern_field_1",
                "pattern_field_2",
                "pattern_field_3",
                "required_field_1",
                "required_field_2",
                "required_field_3",
            ],
            "properties": {
                "enum_field_1": {
                    "type": "string",
                    "enum": ["A", "B", "C"],
                    "errorMessage": {"enum": "enum_field_1 must be A, B, or C. Performance test field 1."},
                },
                "enum_field_2": {
                    "type": "string",
                    "enum": ["X", "Y", "Z"],
                    "errorMessage": {"enum": "enum_field_2 must be X, Y, or Z. Performance test field 2."},
                },
                "enum_field_3": {
                    "type": "string",
                    "enum": ["1", "2", "3"],
                    "errorMessage": {"enum": "enum_field_3 must be 1, 2, or 3. Performance test field 3."},
                },
                "pattern_field_1": {
                    "type": "string",
                    "pattern": "^[A-Z]{2}[0-9]{2}$",
                    "errorMessage": {"regex": "pattern_field_1 must be 2 uppercase letters followed by 2 digits."},
                },
                "pattern_field_2": {
                    "type": "string",
                    "pattern": "^[0-9]{3}-[0-9]{3}$",
                    "errorMessage": {"regex": "pattern_field_2 must be in format XXX-XXX where X is a digit."},
                },
                "pattern_field_3": {
                    "type": "string",
                    "pattern": "^[a-z]+@[a-z]+\\.[a-z]{2,3}$",
                    "errorMessage": {"regex": "pattern_field_3 must be a valid email format."},
                },
                "required_field_1": {
                    "type": "string",
                    "minLength": 1,
                    "errorMessage": {"general": "required_field_1 is mandatory and cannot be empty."},
                },
                "required_field_2": {
                    "type": "string",
                    "minLength": 1,
                    "errorMessage": {"general": "required_field_2 is mandatory and cannot be empty."},
                },
                "required_field_3": {
                    "type": "string",
                    "minLength": 1,
                    "errorMessage": {"general": "required_field_3 is mandatory and cannot be empty."},
                },
                # Fields without custom messages for comparison
                "no_custom_enum": {"type": "string", "enum": ["option1", "option2"]},
                "no_custom_pattern": {"type": "string", "pattern": "^[0-9]+$"},
            },
        }

    @pytest.fixture
    def sample_catalog(self):
        """Create a sample catalog for performance testing."""
        return [
            {
                "core_uuid": "performance_core",
                "core_name": "Performance Core Schema",
                "core_path": "performance_core.json",
                "program": [
                    {
                        "program_uuid": "performance_program",
                        "program_name": "Performance Program Schema",
                        "program_path": "performance_program.json",
                    }
                ],
            }
        ]

    @pytest.fixture
    def temp_schema_directory(self, performance_schema_with_custom_messages, sample_catalog):
        """Create a temporary directory with performance test schema files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write catalog.json
            catalog_path = temp_path / "catalog.json"
            with open(catalog_path, "w") as f:
                json.dump(sample_catalog, f)

            # Write core schema (empty for this test)
            core_schema_path = temp_path / "performance_core.json"
            with open(core_schema_path, "w") as f:
                json.dump({"type": "object", "properties": {}}, f)

            # Write program schema with performance test custom error messages
            program_schema_path = temp_path / "performance_program.json"
            with open(program_schema_path, "w") as f:
                json.dump(performance_schema_with_custom_messages, f)

            yield str(temp_path)

    @pytest.fixture
    def schema_collector(self, temp_schema_directory):
        """Create a FileBasedSchemaCollector for performance testing."""
        return FileBasedSchemaCollector(temp_schema_directory)

    @pytest.fixture
    def validation_node(self, schema_collector):
        """Create a ValidationNode for performance testing."""
        return ValidationNode(schema_collector)

    def create_performance_dataframe(self, size: int) -> pd.DataFrame:
        """Create a DataFrame of specified size for performance testing."""
        # Create data that will trigger various validation errors
        data = {
            "enum_field_1": ["invalid"] * size,
            "enum_field_2": ["invalid"] * size,
            "enum_field_3": ["invalid"] * size,
            "pattern_field_1": ["invalid"] * size,
            "pattern_field_2": ["invalid"] * size,
            "pattern_field_3": ["invalid"] * size,
            "required_field_1": [""] * size,  # Empty values
            "required_field_2": [""] * size,
            "required_field_3": [""] * size,
            "no_custom_enum": ["invalid"] * size,
            "no_custom_pattern": ["invalid"] * size,
        }
        return pd.DataFrame(data)

    @pytest.mark.asyncio
    async def test_small_dataset_performance(self, validation_node):
        """Test performance with small dataset (100 rows)."""
        df = self.create_performance_dataframe(100)

        state = ProcessorState(
            aligned_df=df, program_id="performance_program", core_id="performance_core", job_id="small_performance_test"
        )

        # Measure processing time
        start_time = time.time()

        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        processing_time = time.time() - start_time

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None

        # Performance assertion - small dataset should be very fast
        assert processing_time < 2.0, f"Small dataset processing took {processing_time:.3f}s, expected < 2.0s"

        # Verify results quality
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors (11 fields * 100 rows = up to 1100 errors)
        assert len(errors) > 500

        # Verify custom messages are properly applied
        custom_message_errors = [e for e in errors if e.error_message is not None]
        system_message_errors = [e for e in errors if e.error_message is None]

        assert len(custom_message_errors) > 400  # 9 fields with custom messages
        assert len(system_message_errors) > 100  # 2 fields without custom messages

        print(
            f"Small dataset (100 rows): {processing_time:.3f}s, {len(errors)} errors, {len(custom_message_errors)} custom messages"
        )

    @pytest.mark.asyncio
    async def test_medium_dataset_performance(self, validation_node):
        """Test performance with medium dataset (1000 rows)."""
        df = self.create_performance_dataframe(1000)

        state = ProcessorState(
            aligned_df=df,
            program_id="performance_program",
            core_id="performance_core",
            job_id="medium_performance_test",
        )

        # Measure processing time
        start_time = time.time()

        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        processing_time = time.time() - start_time

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None

        # Performance assertion - medium dataset should complete within reasonable time
        assert processing_time < 5.0, f"Medium dataset processing took {processing_time:.3f}s, expected < 5.0s"

        # Verify results quality
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors
        assert len(errors) > 5000

        # Verify custom messages are properly applied
        custom_message_errors = [e for e in errors if e.error_message is not None]
        system_message_errors = [e for e in errors if e.error_message is None]

        assert len(custom_message_errors) > 4000
        assert len(system_message_errors) > 1000

        print(
            f"Medium dataset (1000 rows): {processing_time:.3f}s, {len(errors)} errors, {len(custom_message_errors)} custom messages"
        )

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, validation_node):
        """Test performance with large dataset (5000 rows)."""
        df = self.create_performance_dataframe(5000)

        state = ProcessorState(
            aligned_df=df, program_id="performance_program", core_id="performance_core", job_id="large_performance_test"
        )

        # Measure processing time
        start_time = time.time()

        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        processing_time = time.time() - start_time

        # Verify successful execution
        assert result.status.name == "COMPLETED"
        assert state.combined_results is not None

        # Performance assertion - large dataset should complete within reasonable time
        assert processing_time < 15.0, f"Large dataset processing took {processing_time:.3f}s, expected < 15.0s"

        # Verify results quality
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have many errors
        assert len(errors) > 25000

        # Verify custom messages are properly applied
        custom_message_errors = [e for e in errors if e.error_message is not None]
        system_message_errors = [e for e in errors if e.error_message is None]

        assert len(custom_message_errors) > 20000
        assert len(system_message_errors) > 5000

        print(
            f"Large dataset (5000 rows): {processing_time:.3f}s, {len(errors)} errors, {len(custom_message_errors)} custom messages"
        )

    @pytest.mark.asyncio
    async def test_api_conversion_performance(self, validation_node):
        """Test performance of converting processor results to API format."""
        df = self.create_performance_dataframe(2000)

        state = ProcessorState(
            aligned_df=df,
            program_id="performance_program",
            core_id="performance_core",
            job_id="api_conversion_performance_test",
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        assert result.status.name == "COMPLETED"

        # Get processor results
        processor_results = state.combined_results.validation_results
        processor_errors = processor_results.validation_results

        # Measure API conversion time
        conversion_start = time.time()

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

        conversion_time = time.time() - conversion_start

        # Performance assertion - API conversion should be fast
        assert conversion_time < 3.0, f"API conversion took {conversion_time:.3f}s, expected < 3.0s"

        # Measure serialization time
        serialization_start = time.time()

        api_results = ValidationResults(
            validation_results=api_errors,
            summary=ValidationResultsSummary(
                total_rows=processor_results.summary.total_rows,
                total_errors=processor_results.summary.total_errors,
                error_types=processor_results.summary.error_types,
                columns_validated=processor_results.summary.columns_validated,
            ),
        )

        serialized = api_results.model_dump(by_alias=True)

        serialization_time = time.time() - serialization_start

        # Performance assertion - serialization should be fast
        assert serialization_time < 2.0, f"Serialization took {serialization_time:.3f}s, expected < 2.0s"

        # Verify data integrity
        assert len(serialized["validationResults"]) == len(processor_errors)

        print(
            f"API conversion (2000 rows, {len(processor_errors)} errors): conversion={conversion_time:.3f}s, serialization={serialization_time:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_memory_usage_performance(self, validation_node):
        """Test memory usage during custom error message processing."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        df = self.create_performance_dataframe(3000)

        state = ProcessorState(
            aligned_df=df,
            program_id="performance_program",
            core_id="performance_core",
            job_id="memory_performance_test",
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        post_processing_memory = process.memory_info().rss / 1024 / 1024  # MB
        processing_memory_increase = post_processing_memory - initial_memory

        # Memory increase should be reasonable
        assert (
            processing_memory_increase < 200
        ), f"Processing memory increased by {processing_memory_increase:.2f}MB, expected < 200MB"

        # Get results and convert to API format
        processor_results = state.combined_results.validation_results
        processor_errors = processor_results.validation_results

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

        post_api_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = post_api_memory - initial_memory

        # Total memory increase should still be reasonable
        assert total_memory_increase < 300, f"Total memory increased by {total_memory_increase:.2f}MB, expected < 300MB"

        print(
            f"Memory usage (3000 rows, {len(processor_errors)} errors): processing={processing_memory_increase:.2f}MB, total={total_memory_increase:.2f}MB"
        )

    @pytest.mark.asyncio
    async def test_concurrent_validation_performance(self, validation_node):
        """Test performance of concurrent validation processing."""

        async def run_concurrent_validation(job_id: str, size: int):
            """Run a single validation job concurrently."""
            df = self.create_performance_dataframe(size)

            state = ProcessorState(
                aligned_df=df, program_id="performance_program", core_id="performance_core", job_id=job_id
            )

            start_time = time.time()

            result = await validation_node.invoke_async(
                task="validation_task", invocation_state={"processor_state": state}
            )

            processing_time = time.time() - start_time

            return state, result, processing_time

        # Run multiple validations concurrently
        concurrent_tasks = [run_concurrent_validation(f"concurrent_job_{i}", 500) for i in range(3)]

        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks)
        total_time = time.time() - start_time

        # Verify all validations completed successfully
        for state, result, processing_time in results:
            assert result.status.name == "COMPLETED"
            assert state.combined_results is not None

            # Individual processing should be reasonable
            assert (
                processing_time < 5.0
            ), f"Individual concurrent processing took {processing_time:.3f}s, expected < 5.0s"

            # Verify custom error messages are properly extracted
            validation_results = state.combined_results.validation_results
            errors = validation_results.validation_results

            custom_message_errors = [e for e in errors if e.error_message is not None]
            assert len(custom_message_errors) > 2000

        # Total concurrent time should be less than sum of individual times
        individual_times = [processing_time for _, _, processing_time in results]
        sum_individual_times = sum(individual_times)

        # Concurrent execution should not be significantly slower than sequential
        assert (
            total_time < sum_individual_times * 1.5
        ), f"Concurrent execution took {total_time:.3f}s, expected < {sum_individual_times * 1.5:.3f}s"

        print(f"Concurrent validation (3 jobs, 500 rows each): total={total_time:.3f}s, individual={individual_times}")

    def test_error_message_extraction_performance(self, validation_node):
        """Test performance of error message extraction from schema definitions."""
        # Test different error message formats
        test_cases = [
            # Dictionary format with multiple message types
            {
                "error_message": {
                    "enum": "Enum error message",
                    "regex": "Regex error message",
                    "general": "General error message",
                }
            },
            # String format
            {"error_message": "Simple string error message"},
            # Complex dictionary with many entries
            {"error_message": {f"type_{i}": f"Error message for type {i}" for i in range(20)}},
        ]

        # Measure extraction performance
        start_time = time.time()

        for _ in range(1000):  # Repeat extraction many times
            for test_case in test_cases:
                error_messages = validation_node._extract_error_messages(test_case)
                assert len(error_messages) > 0

        extraction_time = time.time() - start_time

        # Performance assertion - extraction should be very fast
        assert extraction_time < 0.5, f"Error message extraction took {extraction_time:.3f}s, expected < 0.5s"

        print(f"Error message extraction (3000 extractions): {extraction_time:.3f}s")

    @pytest.mark.asyncio
    async def test_scalability_comparison(self, validation_node):
        """Test scalability by comparing performance across different dataset sizes."""
        sizes = [100, 500, 1000, 2000]
        results = []

        for size in sizes:
            df = self.create_performance_dataframe(size)

            state = ProcessorState(
                aligned_df=df,
                program_id="performance_program",
                core_id="performance_core",
                job_id=f"scalability_test_{size}",
            )

            start_time = time.time()

            result = await validation_node.invoke_async(
                task="validation_task", invocation_state={"processor_state": state}
            )

            processing_time = time.time() - start_time

            assert result.status.name == "COMPLETED"

            validation_results = state.combined_results.validation_results
            errors = validation_results.validation_results
            custom_message_errors = [e for e in errors if e.error_message is not None]

            results.append(
                {
                    "size": size,
                    "time": processing_time,
                    "errors": len(errors),
                    "custom_messages": len(custom_message_errors),
                    "time_per_row": processing_time / size,
                    "time_per_error": processing_time / len(errors) if len(errors) > 0 else 0,
                }
            )

            print(
                f"Size {size}: {processing_time:.3f}s, {len(errors)} errors, {len(custom_message_errors)} custom messages"
            )

        # Verify scalability characteristics
        for i in range(1, len(results)):
            prev_result = results[i - 1]
            curr_result = results[i]

            # Time per row should not increase significantly (allow 5x for system noise
            # and fixed-overhead effects at small dataset sizes)
            time_per_row_ratio = curr_result["time_per_row"] / prev_result["time_per_row"]
            assert time_per_row_ratio < 5.0, f"Time per row increased by {time_per_row_ratio:.2f}x, expected < 5.0x"

            # Time per error should remain relatively stable
            if prev_result["time_per_error"] > 0 and curr_result["time_per_error"] > 0:
                time_per_error_ratio = curr_result["time_per_error"] / prev_result["time_per_error"]
                assert (
                    time_per_error_ratio < 5.0
                ), f"Time per error increased by {time_per_error_ratio:.2f}x, expected < 5.0x"

        print("Scalability test completed successfully")
        for result in results:
            print(
                f"  Size {result['size']}: {result['time']:.3f}s ({result['time_per_row']:.6f}s/row, {result['time_per_error']:.6f}s/error)"
            )
