# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for schema alignment utilities.

This module tests the basic schema alignment functionality that converts
snake_case column names to camelCase for demonstration purposes.
"""

from datetime import datetime

import pandas as pd

from metadata_harmonization_processor.utils.schema_alignment_utils import (
    apply_basic_schema_alignment,
    create_basic_column_mapping,
    create_example_schema_alignment_results,
    create_transformation_summary,
    dataframe_to_csv_string,
    snake_to_camel_case,
)


class TestSnakeToCamelCase:
    """Test snake_case to camelCase conversion."""

    def test_simple_conversion(self):
        """Test basic snake_case to camelCase conversion."""
        assert snake_to_camel_case("patient_id") == "patientId"
        assert snake_to_camel_case("sample_date") == "sampleDate"
        assert snake_to_camel_case("lab_result") == "labResult"

    def test_multiple_underscores(self):
        """Test conversion with multiple underscores."""
        assert snake_to_camel_case("sample_collection_date") == "sampleCollectionDate"
        assert snake_to_camel_case("host_scientific_name") == "hostScientificName"
        assert snake_to_camel_case("sequencing_protocol_primer_set") == "sequencingProtocolPrimerSet"

    def test_single_word(self):
        """Test conversion of single words (no underscores)."""
        assert snake_to_camel_case("patient") == "patient"
        assert snake_to_camel_case("sample") == "sample"
        assert snake_to_camel_case("result") == "result"

    def test_empty_string(self):
        """Test conversion of empty string."""
        assert snake_to_camel_case("") == ""


class TestColumnMapping:
    """Test column mapping creation."""

    def test_basic_mapping(self):
        """Test basic column mapping creation."""
        columns = ["patient_id", "sample_date", "lab_result"]
        expected = {
            "patient_id": "patientId",
            "sample_date": "sampleDate",
            "lab_result": "labResult",
        }
        assert create_basic_column_mapping(columns) == expected

    def test_mixed_columns(self):
        """Test mapping with mixed snake_case and regular columns."""
        columns = ["patient_id", "name", "sample_date", "age"]
        expected = {
            "patient_id": "patientId",
            "name": "name",
            "sample_date": "sampleDate",
            "age": "age",
        }
        assert create_basic_column_mapping(columns) == expected

    def test_empty_list(self):
        """Test mapping with empty column list."""
        assert create_basic_column_mapping([]) == {}


class TestSchemaAlignment:
    """Test schema alignment application."""

    def test_basic_alignment(self):
        """Test basic schema alignment on DataFrame."""
        df = pd.DataFrame(
            {
                "patient_id": [1, 2, 3],
                "sample_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
                "lab_result": [45.2, 38.7, 52.1],
            }
        )

        aligned_df, mappings = apply_basic_schema_alignment(df)

        # Check column names were converted
        expected_columns = ["patientId", "sampleDate", "labResult"]
        assert list(aligned_df.columns) == expected_columns

        # Check data is preserved
        assert len(aligned_df) == 3
        assert aligned_df["patientId"].tolist() == [1, 2, 3]

        # Check mappings
        expected_mappings = {
            "patient_id": "patientId",
            "sample_date": "sampleDate",
            "lab_result": "labResult",
        }
        assert mappings == expected_mappings

    def test_mixed_columns_alignment(self):
        """Test alignment with mixed column types."""
        df = pd.DataFrame(
            {
                "patient_id": [1, 2],
                "name": ["John", "Jane"],
                "sample_date": ["2023-01-01", "2023-01-02"],
            }
        )

        aligned_df, mappings = apply_basic_schema_alignment(df)

        # Check mixed column conversion
        expected_columns = ["patientId", "name", "sampleDate"]
        assert list(aligned_df.columns) == expected_columns

        # Check mappings include unchanged columns
        expected_mappings = {
            "patient_id": "patientId",
            "name": "name",
            "sample_date": "sampleDate",
        }
        assert mappings == expected_mappings


class TestTransformationSummary:
    """Test transformation summary creation."""

    def test_basic_summary(self):
        """Test basic transformation summary."""
        original_df = pd.DataFrame({"patient_id": [1, 2], "sample_date": ["2023-01-01", "2023-01-02"]})

        aligned_df = pd.DataFrame({"patientId": [1, 2], "sampleDate": ["2023-01-01", "2023-01-02"]})

        column_mapping = {"patient_id": "patientId", "sample_date": "sampleDate"}

        summary = create_transformation_summary(original_df, aligned_df, column_mapping)

        assert summary["columns_renamed"] == 2
        assert summary["columns_added"] == 0
        assert summary["columns_removed"] == 0
        assert summary["rows_original"] == 2
        assert summary["rows_aligned"] == 2
        assert summary["transformation_type"] == "snake_case_to_camel_case"
        assert "processing_timestamp" in summary


class TestCSVConversion:
    """Test DataFrame to CSV conversion."""

    def test_basic_csv_conversion(self):
        """Test basic DataFrame to CSV string conversion."""
        df = pd.DataFrame({"patientId": [1, 2], "sampleDate": ["2023-01-01", "2023-01-02"]})

        csv_string = dataframe_to_csv_string(df)

        # Check CSV format
        lines = csv_string.strip().split("\n")
        assert lines[0] == "patientId,sampleDate"
        assert lines[1] == "1,2023-01-01"
        assert lines[2] == "2,2023-01-02"


class TestExampleResults:
    """Test example schema alignment results creation."""

    def test_create_example_results(self):
        """Test creation of example SchemaAlignmentResults."""
        job_id = "test-job-123"
        version = 1

        results = create_example_schema_alignment_results(job_id, version)

        # Check basic properties
        assert results.job_id == job_id
        assert results.version == version
        assert isinstance(results.timestamp, datetime)

        # Check CSV data exists
        assert len(results.original_data_csv) > 0
        assert len(results.aligned_data_csv) > 0

        # Check column mappings
        assert "patient_id" in results.column_mappings
        assert results.column_mappings["patient_id"] == "patientId"
        assert "sample_collection_date" in results.column_mappings
        assert results.column_mappings["sample_collection_date"] == "sampleCollectionDate"

        # Check transformation summary
        assert results.transformation_summary["columns_renamed"] > 0
        assert results.transformation_summary["transformation_type"] == "snake_case_to_camel_case"

        # Check CSV headers are different
        original_lines = results.original_data_csv.strip().split("\n")
        aligned_lines = results.aligned_data_csv.strip().split("\n")

        # Original should have snake_case headers
        assert "patient_id" in original_lines[0]
        assert "sample_collection_date" in original_lines[0]

        # Aligned should have camelCase headers
        assert "patientId" in aligned_lines[0]
        assert "sampleCollectionDate" in aligned_lines[0]

    def test_serialization(self):
        """Test that results can be serialized and deserialized."""
        job_id = "test-job-456"
        results = create_example_schema_alignment_results(job_id)

        # Test to_dict conversion
        data_dict = results.to_dict()
        assert "summary" in data_dict
        assert data_dict["summary"]["job_id"] == job_id
        assert "timestamp" in data_dict["summary"]
        assert isinstance(data_dict["summary"]["timestamp"], str)  # Should be ISO format
        assert "schema_alignment_results" in data_dict
        assert isinstance(data_dict["schema_alignment_results"], list)

        # Test from_dict conversion
        restored_results = results.__class__.from_dict(data_dict)
        assert restored_results.job_id == results.job_id
        assert restored_results.version == results.version
        assert restored_results.column_mappings == results.column_mappings
