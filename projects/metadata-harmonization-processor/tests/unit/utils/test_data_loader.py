# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for schema-aware data loading utilities."""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from metadata_harmonization_processor.utils.data_loader import load_metadata_csv


class TestLoadMetadataCSV:
    """Tests for load_metadata_csv function."""

    @pytest.mark.asyncio
    async def test_load_csv_with_boolean_strings(self, tmp_path):
        """Test that boolean strings like FALSE/TRUE are preserved as strings."""
        # Create test CSV
        csv_content = "cold_adapted,deceased,sample_id\nFALSE,TRUE,S001\nTRUE,FALSE,S002\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(
            return_value={
                "properties": {
                    "cold_adapted": {"type": "string", "enum": ["TRUE", "FALSE", ""]},
                    "deceased": {"type": "string", "enum": ["TRUE", "FALSE", ""]},
                    "sample_id": {"type": "string"},
                }
            }
        )

        # Load CSV
        df = await load_metadata_csv(str(csv_file), "test_program", "test_core", mock_schema_collector)

        # Verify data types
        assert df["cold_adapted"].dtype == object  # str columns have dtype object
        assert df["deceased"].dtype == object
        assert df["sample_id"].dtype == object

        # Verify values are preserved as strings
        assert df["cold_adapted"].iloc[0] == "FALSE"
        assert df["cold_adapted"].iloc[1] == "TRUE"
        assert df["deceased"].iloc[0] == "TRUE"
        assert df["deceased"].iloc[1] == "FALSE"

    @pytest.mark.asyncio
    async def test_load_csv_with_numeric_strings(self, tmp_path):
        """Test that numeric-looking strings defined as string type stay as strings."""
        # Create test CSV
        csv_content = "passage_number,CSID,age\n9,612074123,25\n15,612074124,30\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector - all defined as strings
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(
            return_value={
                "properties": {
                    "passage_number": {"type": "string", "pattern": "^\\d*$"},
                    "CSID": {"type": "string"},
                    "age": {"type": "string", "pattern": "^\\d*$"},
                }
            }
        )

        # Load CSV
        df = await load_metadata_csv(str(csv_file), "test_program", "test_core", mock_schema_collector)

        # Verify all are strings
        assert df["passage_number"].dtype == object
        assert df["CSID"].dtype == object
        assert df["age"].dtype == object

        # Verify values preserved without .0
        assert df["passage_number"].iloc[0] == "9"  # Not "9.0"
        assert df["CSID"].iloc[0] == "612074123"
        assert df["age"].iloc[0] == "25"  # Not "25.0"

    @pytest.mark.asyncio
    async def test_load_csv_with_actual_numeric_types(self, tmp_path):
        """Test that fields with numeric schema types are loaded correctly."""
        # Create test CSV
        csv_content = "name,age,score\nAlice,25,95.5\nBob,30,87.2\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector with actual numeric types
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(
            return_value={
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "score": {"type": "number"},
                }
            }
        )

        # Load CSV
        df = await load_metadata_csv(str(csv_file), "test_program", "test_core", mock_schema_collector)

        # Verify types
        assert df["name"].dtype == object  # string
        assert df["age"].dtype == np.int64  # integer
        assert df["score"].dtype == np.float64  # number

        # Verify values
        assert df["name"].iloc[0] == "Alice"
        assert df["age"].iloc[0] == 25
        assert df["score"].iloc[0] == 95.5

    @pytest.mark.asyncio
    async def test_load_csv_with_extra_columns(self, tmp_path):
        """Test that columns not in schema are converted to strings."""
        # Create test CSV with extra column
        csv_content = "field1,field2,extra_field\nvalue1,value2,123\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector - only defines field1 and field2
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(
            return_value={
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"},
                }
            }
        )

        # Load CSV
        df = await load_metadata_csv(str(csv_file), "test_program", "test_core", mock_schema_collector)

        # Verify extra column is converted to string
        assert df["extra_field"].dtype == object
        assert df["extra_field"].iloc[0] == "123"  # String, not int

    @pytest.mark.asyncio
    async def test_load_csv_with_extra_boolean_columns(self, tmp_path):
        """Test that extra columns with boolean-like values are loaded as strings, not bools."""
        # Create test CSV with extra column containing boolean-like strings
        csv_content = "field1,extra_bool_field,extra_numeric\nvalue1,FALSE,9\nvalue2,TRUE,15\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector - only defines field1, not the extra columns
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(return_value={"properties": {"field1": {"type": "string"}}})

        # Load CSV
        df = await load_metadata_csv(str(csv_file), "test_program", "test_core", mock_schema_collector)

        # Verify extra boolean-like column is loaded as string, NOT converted to bool
        assert df["extra_bool_field"].dtype == object  # String columns have dtype object
        assert df["extra_bool_field"].iloc[0] == "FALSE"  # NOT False (bool) or "False" (str)
        assert df["extra_bool_field"].iloc[1] == "TRUE"  # NOT True (bool) or "True" (str)
        assert isinstance(df["extra_bool_field"].iloc[0], str)  # Verify it's actually a string

        # Verify extra numeric column is also loaded as string
        assert df["extra_numeric"].dtype == object
        assert df["extra_numeric"].iloc[0] == "9"  # String "9", not int 9
        assert df["extra_numeric"].iloc[1] == "15"  # String "15", not int 15

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, tmp_path):
        """Test that FileNotFoundError is raised for missing file."""
        mock_schema_collector = MagicMock()

        with pytest.raises(FileNotFoundError):
            await load_metadata_csv(
                str(tmp_path / "nonexistent.csv"),
                "test_program",
                "test_core",
                mock_schema_collector,
            )

    @pytest.mark.asyncio
    async def test_schema_collector_called_correctly(self, tmp_path):
        """Test that schema collector is called with correct parameters."""
        # Create test CSV
        csv_content = "field1\nvalue1\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock schema collector
        mock_schema_collector = MagicMock()
        mock_schema_collector.get_schema = AsyncMock(return_value={"properties": {"field1": {"type": "string"}}})

        # Load CSV
        await load_metadata_csv(str(csv_file), "my_program_id", "my_core_id", mock_schema_collector)

        # Verify schema collector was called with correct params
        mock_schema_collector.get_schema.assert_called_once_with("my_program_id", "my_core_id")
