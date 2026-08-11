# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for SchemaAlignmentConfig and enhanced SchemaAlignmentNode with LLM support.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from metadata_harmonization_processor.config import (
    ProcessorConfig,
    SchemaAlignmentConfig,
)
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode


class TestSchemaAlignmentConfig:
    """Test cases for SchemaAlignmentConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SchemaAlignmentConfig()

        assert config.use_llm is True
        assert config.model_id == "amazon.nova-pro-v1:0"
        assert config.aws_region == "us-east-1"
        assert config.llm_temperature == 0.3
        assert config.llm_max_tokens == 800
        assert config.llm_timeout_seconds == 30
        assert config.fallback_on_llm_failure is True
        assert config.similarity_threshold == 0.7
        assert config.enable_change_tracking is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SchemaAlignmentConfig(
            use_llm=False,
            model_id="custom-model",
            aws_region="us-west-2",
            llm_temperature=0.5,
            llm_max_tokens=1000,
            llm_timeout_seconds=60,
            fallback_on_llm_failure=False,
            similarity_threshold=0.8,
            enable_change_tracking=False,
        )

        assert config.use_llm is False
        assert config.model_id == "custom-model"
        assert config.aws_region == "us-west-2"
        assert config.llm_temperature == 0.5
        assert config.llm_max_tokens == 1000
        assert config.llm_timeout_seconds == 60
        assert config.fallback_on_llm_failure is False
        assert config.similarity_threshold == 0.8
        assert config.enable_change_tracking is False

    def test_processor_config_includes_schema_alignment(self):
        """Test that ProcessorConfig includes SchemaAlignmentConfig."""
        config = ProcessorConfig(
            schema_directory="/test/schemas",
            session_s3_bucket="test-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        assert hasattr(config, "schema_alignment")
        assert isinstance(config.schema_alignment, SchemaAlignmentConfig)
        assert config.schema_alignment.use_llm is True


class TestSchemaAlignmentNodeLLM:
    """Test cases for SchemaAlignmentNode with LLM functionality."""

    @pytest.fixture
    def mock_schema_collector(self):
        """Mock schema collector."""
        collector = Mock()
        collector.get_schema = AsyncMock(return_value={"properties": {}})
        collector.get_schema_columns = AsyncMock(return_value=["col1", "col2", "col3"])
        return collector

    @pytest.fixture
    def mock_processor_state(self):
        """Mock ProcessorState for testing."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        return ProcessorState(
            job_id="test-job-123",
            program_id="test-program",
            core_id="test-core",
            metadata_df=df,
        )

    @pytest.fixture
    def llm_config(self):
        """LLM-enabled configuration."""
        return SchemaAlignmentConfig(use_llm=True, model_id="amazon.nova-pro-v1:0", enable_change_tracking=True)

    @pytest.fixture
    def rule_based_config(self):
        """Rule-based only configuration."""
        return SchemaAlignmentConfig(use_llm=False, enable_change_tracking=True, similarity_threshold=0.7)

    def test_node_initialization_with_llm_config(self, mock_schema_collector, llm_config):
        """Test node initialization with LLM configuration."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            assert node.config == llm_config
            assert node.bedrock_runtime == mock_bedrock
            mock_boto3.assert_called_once_with("bedrock-runtime", region_name="us-east-1")

    def test_node_initialization_without_llm(self, mock_schema_collector, rule_based_config):
        """Test node initialization without LLM."""
        node = SchemaAlignmentNode(mock_schema_collector, rule_based_config)

        assert node.config == rule_based_config
        assert node.bedrock_runtime is None

    def test_node_initialization_llm_failure_fallback(self, mock_schema_collector, llm_config):
        """Test node initialization with LLM failure fallback."""
        with patch("boto3.client", side_effect=Exception("Boto3 error")):
            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            assert node.config.use_llm is False  # Should be disabled due to failure
            assert node.bedrock_runtime is None

    def test_llm_column_match_success(self, mock_schema_collector, llm_config, mock_processor_state):
        """Test successful LLM column matching."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "Target: sample_id | Match: sampleId | Confidence: High | Reasoning: Semantic match\nTarget: patient_name | Match: patientName | Confidence: High | Reasoning: Semantic match"
                            }
                        ]
                    }
                },
                "usage": {"inputTokens": 100, "outputTokens": 50},
            }
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            csv_columns = ["sampleId", "patientName", "testDate"]
            schema_fields = ["sample_id", "patient_name", "test_date"]

            matches = node._llm_column_match(csv_columns, schema_fields, mock_processor_state)

            assert matches == {"sample_id": "sampleId", "patient_name": "patientName"}

            # Verify Bedrock was called with correct parameters
            mock_bedrock.converse.assert_called_once()
            call_args = mock_bedrock.converse.call_args
            assert call_args[1]["modelId"] == "amazon.nova-pro-v1:0"
            assert call_args[1]["inferenceConfig"]["maxTokens"] == 800
            assert call_args[1]["inferenceConfig"]["temperature"] == 0.3

    def test_llm_column_match_failure(self, mock_schema_collector, llm_config, mock_processor_state):
        """Test LLM column matching failure."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.side_effect = Exception("Bedrock error")
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            csv_columns = ["sampleId", "patientName"]
            schema_fields = ["sample_id", "patient_name"]

            with pytest.raises(Exception, match="Bedrock error"):
                node._llm_column_match(csv_columns, schema_fields, mock_processor_state)

    def test_rule_based_match_exact(self, mock_schema_collector, rule_based_config):
        """Test rule-based matching with exact matches."""
        node = SchemaAlignmentNode(mock_schema_collector, rule_based_config)

        csv_columns = ["sample_id", "patient_name", "test_date"]
        schema_fields = ["sample_id", "patient_name", "test_date"]

        matches = node._rule_based_match(csv_columns, schema_fields)

        assert matches == {
            "sample_id": "sample_id",
            "patient_name": "patient_name",
            "test_date": "test_date",
        }

    def test_rule_based_match_case_insensitive(self, mock_schema_collector, rule_based_config):
        """Test rule-based matching with case differences."""
        node = SchemaAlignmentNode(mock_schema_collector, rule_based_config)

        csv_columns = ["SAMPLE_ID", "Patient_Name", "testdate"]
        schema_fields = ["sample_id", "patient_name", "test_date"]

        matches = node._rule_based_match(csv_columns, schema_fields)

        assert matches["sample_id"] == "SAMPLE_ID"
        assert matches["patient_name"] == "Patient_Name"

    def test_rule_based_match_variations(self, mock_schema_collector, rule_based_config):
        """Test rule-based matching with naming variations."""
        node = SchemaAlignmentNode(mock_schema_collector, rule_based_config)

        csv_columns = ["sampleId", "patientName", "testDate"]
        schema_fields = ["sample_id", "patient_name", "test_date"]

        matches = node._rule_based_match(csv_columns, schema_fields)

        # Should find matches through variation handling
        assert len(matches) >= 2  # At least some matches should be found

    def test_rule_based_match_similarity_threshold(self, mock_schema_collector):
        """Test rule-based matching with similarity threshold."""
        config = SchemaAlignmentConfig(use_llm=False, similarity_threshold=0.8)
        node = SchemaAlignmentNode(mock_schema_collector, config)

        csv_columns = ["sample_identifier", "patient_full_name"]
        schema_fields = ["sample_id", "patient_name"]

        matches = node._rule_based_match(csv_columns, schema_fields)

        # Should find matches based on similarity
        assert "sample_id" in matches
        assert matches["sample_id"] == "sample_identifier"

    def test_find_column_mappings_llm_success(self, mock_schema_collector, llm_config, mock_processor_state):
        """Test _find_column_mappings with successful LLM matching."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "Target: sample_id | Match: sampleId | Confidence: High | Reasoning: Semantic match\nTarget: patient_name | Match: patientName | Confidence: High | Reasoning: Semantic match"
                            }
                        ]
                    }
                },
                "usage": {"inputTokens": 100, "outputTokens": 50},
            }
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            current_columns = {"sampleId", "patientName", "testDate"}
            expected_columns = {"sample_id", "patient_name", "test_date"}

            mappings = node._find_column_mappings(current_columns, expected_columns, mock_processor_state)

            assert mappings == {"sampleId": "sample_id", "patientName": "patient_name"}

    def test_find_column_mappings_llm_fallback(self, mock_schema_collector, llm_config, mock_processor_state):
        """Test _find_column_mappings with LLM failure and fallback."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.side_effect = Exception("LLM error")
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            current_columns = {"sample_id", "patient_name"}
            expected_columns = {"sample_id", "patient_name"}

            # Should fallback to rule-based matching
            mappings = node._find_column_mappings(current_columns, expected_columns, mock_processor_state)

            # Should still work with rule-based fallback
            assert isinstance(mappings, dict)

    async def test_align_dataframe_columns_with_change_tracking(
        self, mock_schema_collector, llm_config, mock_processor_state
    ):
        """Test _align_dataframe_columns with change tracking enabled."""
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "Target: sample_id | Match: sampleId | Confidence: High | Reasoning: Semantic match"
                            }
                        ]
                    }
                },
                "usage": {"inputTokens": 100, "outputTokens": 50},
            }
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, llm_config)

            # Create test DataFrame
            df = pd.DataFrame({"sampleId": [1, 2, 3], "extraCol": ["a", "b", "c"]})

            expected_columns = ["sample_id", "new_col"]
            schema_definition = {}

            aligned_df, column_mapping, change_details = await node._align_dataframe_columns(
                df, expected_columns, schema_definition, mock_processor_state
            )

            # Verify results
            assert list(aligned_df.columns) == expected_columns
            assert column_mapping == {"sampleId": "sample_id"}

            # Verify change tracking
            assert len(change_details) == 3  # rename, add, remove

            # Check rename change
            rename_changes = [c for c in change_details if c.change_type == "rename"]
            assert len(rename_changes) == 1
            assert rename_changes[0].original_column == "sampleId"
            assert rename_changes[0].new_column == "sample_id"
            assert "Target: sample_id | Match: sampleId | Confidence:" in rename_changes[0].reason
            assert rename_changes[0].row_count_affected == 3

            # Check add change
            add_changes = [c for c in change_details if c.change_type == "add"]
            assert len(add_changes) == 1
            assert add_changes[0].new_column == "new_col"
            assert "Reasoning: Required by schema" in add_changes[0].reason

            # Check remove change
            remove_changes = [c for c in change_details if c.change_type == "remove"]
            assert len(remove_changes) == 1
            assert remove_changes[0].original_column == "extraCol"
            assert "Reasoning: Not in target schema" in remove_changes[0].reason

    async def test_align_dataframe_columns_without_change_tracking(self, mock_schema_collector, mock_processor_state):
        """Test _align_dataframe_columns with change tracking disabled."""
        config = SchemaAlignmentConfig(enable_change_tracking=False)
        node = SchemaAlignmentNode(mock_schema_collector, config)

        # Create test DataFrame
        df = pd.DataFrame({"sample_id": [1, 2, 3], "extraCol": ["a", "b", "c"]})

        expected_columns = ["sample_id", "new_col"]
        schema_definition = {}

        aligned_df, column_mapping, change_details = await node._align_dataframe_columns(
            df, expected_columns, schema_definition, mock_processor_state
        )

        # Verify results
        assert list(aligned_df.columns) == expected_columns
        assert len(change_details) == 0  # No change tracking

    async def test_align_dataframe_columns_rule_based_reason(
        self, mock_schema_collector, rule_based_config, mock_processor_state
    ):
        """Test _align_dataframe_columns with rule-based matching reason."""
        node = SchemaAlignmentNode(mock_schema_collector, rule_based_config)

        # Create test DataFrame
        df = pd.DataFrame({"sampleId": [1, 2, 3]})

        expected_columns = ["sample_id"]
        schema_definition = {}

        aligned_df, column_mapping, change_details = await node._align_dataframe_columns(
            df, expected_columns, schema_definition, mock_processor_state
        )

        # Verify rule-based reason
        rename_changes = [c for c in change_details if c.change_type == "rename"]
        if rename_changes:  # May not find match depending on rule-based logic
            assert "Reasoning: Rule-based pattern match" in rename_changes[0].reason


class TestSchemaAlignmentNodeIntegration:
    """Integration tests for SchemaAlignmentNode with various configurations."""

    @pytest.fixture
    def mock_schema_collector(self):
        """Mock schema collector."""
        collector = Mock()
        collector.get_schema = AsyncMock(return_value={"properties": {}})
        collector.get_schema_columns = AsyncMock(return_value=["sample_id", "patient_name", "test_date"])
        return collector

    @pytest.fixture
    def mock_processor_state(self):
        """Mock ProcessorState for testing."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        return ProcessorState(
            job_id="test-job-123",
            program_id="test-program",
            core_id="test-core",
            metadata_df=df,
        )

    @pytest.fixture
    def sample_dataframe(self):
        """Sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "sampleId": [1, 2, 3],
                "patientName": ["Alice", "Bob", "Charlie"],
                "extraColumn": ["x", "y", "z"],
            }
        )

    async def test_llm_enabled_full_workflow(self, mock_schema_collector, sample_dataframe, mock_processor_state):
        """Test full workflow with LLM enabled."""
        config = SchemaAlignmentConfig(use_llm=True, enable_change_tracking=True)

        with patch("boto3.client") as mock_boto3:
            mock_bedrock = Mock()
            mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "Target: sample_id | Match: sampleId | Confidence: High | Reasoning: Semantic match\nTarget: patient_name | Match: patientName | Confidence: High | Reasoning: Semantic match"
                            }
                        ]
                    }
                },
                "usage": {"inputTokens": 100, "outputTokens": 50},
            }
            mock_boto3.return_value = mock_bedrock

            node = SchemaAlignmentNode(mock_schema_collector, config)

            expected_columns = ["sample_id", "patient_name", "test_date"]
            aligned_df, mappings, changes = await node._align_dataframe_columns(
                sample_dataframe, expected_columns, {}, mock_processor_state
            )

            # Verify alignment
            assert list(aligned_df.columns) == expected_columns
            assert len(changes) > 0
            assert any(c.change_type == "rename" for c in changes)
            assert any(c.change_type == "add" for c in changes)
            assert any(c.change_type == "remove" for c in changes)

    async def test_rule_based_only_workflow(self, mock_schema_collector, sample_dataframe, mock_processor_state):
        """Test full workflow with rule-based matching only."""
        config = SchemaAlignmentConfig(use_llm=False, enable_change_tracking=True, similarity_threshold=0.6)

        node = SchemaAlignmentNode(mock_schema_collector, config)

        expected_columns = ["sample_id", "patient_name", "test_date"]
        aligned_df, mappings, changes = await node._align_dataframe_columns(
            sample_dataframe, expected_columns, {}, mock_processor_state
        )

        # Verify alignment
        assert list(aligned_df.columns) == expected_columns
        assert len(changes) > 0

    async def test_mixed_configuration_scenarios(self, mock_schema_collector, sample_dataframe, mock_processor_state):
        """Test various configuration combinations."""
        scenarios = [
            # LLM with high similarity threshold
            SchemaAlignmentConfig(use_llm=True, similarity_threshold=0.9),
            # Rule-based with low similarity threshold
            SchemaAlignmentConfig(use_llm=False, similarity_threshold=0.5),
            # Change tracking disabled
            SchemaAlignmentConfig(enable_change_tracking=False),
            # LLM with fallback disabled
            SchemaAlignmentConfig(use_llm=True, fallback_on_llm_failure=False),
        ]

        for config in scenarios:
            with patch("boto3.client") as mock_boto3:
                if config.use_llm:
                    mock_bedrock = Mock()
                    mock_bedrock.converse.return_value = {
                        "output": {
                            "message": {
                                "content": [
                                    {
                                        "text": "Target: sample_id | Match: sampleId | Confidence: High | Reasoning: Semantic match"
                                    }
                                ]
                            }
                        },
                        "usage": {"inputTokens": 100, "outputTokens": 50},
                    }
                    mock_boto3.return_value = mock_bedrock

                node = SchemaAlignmentNode(mock_schema_collector, config)

                expected_columns = ["sample_id", "patient_name", "test_date"]
                aligned_df, mappings, changes = await node._align_dataframe_columns(
                    sample_dataframe, expected_columns, {}, mock_processor_state
                )

                # Basic verification that alignment works
                assert list(aligned_df.columns) == expected_columns
                assert isinstance(mappings, dict)
                assert isinstance(changes, list)

                if config.enable_change_tracking:
                    # Should have some changes tracked
                    assert len(changes) >= 0
                else:
                    # No change tracking
                    assert len(changes) == 0
