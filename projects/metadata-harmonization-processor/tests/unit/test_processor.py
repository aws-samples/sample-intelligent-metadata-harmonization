# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for MetadataHarmonizationProcessor class.

This module contains comprehensive unit tests for the main processor class,
including initialization, configuration, processing pipeline orchestration,
error handling, and state management.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.interfaces.schema_collector import (
    SchemaCollector,
    SchemaInfo,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.processor import (
    MetadataHarmonizationProcessor,
    ProcessingError,
)


class MockJobStatusSaver(JobStatusSaver):
    """Mock implementation of JobStatusSaver for testing."""

    def __init__(self):
        self.jobs: dict[str, MetadataUploadJob] = {}
        self.progress_updates: dict[str, dict[str, float]] = {}

    async def save_job(self, job: MetadataUploadJob) -> None:
        """Save complete job information."""
        self.jobs[job.job_id] = job

    async def get_job(self, job_id: str) -> MetadataUploadJob | None:
        """Retrieve job by ID."""
        return self.jobs.get(job_id)

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional fields."""
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            for key, value in kwargs.items():
                if hasattr(self.jobs[job_id], key):
                    setattr(self.jobs[job_id], key, value)

    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Add results for a specific version to the job."""
        if job_id in self.jobs:
            self.jobs[job_id].results[str(version)] = job_results

    async def increment_job_version(self, job_id: str) -> int:
        """Increment the job version and return the new version number."""
        if job_id in self.jobs:
            self.jobs[job_id].current_version += 1
            return self.jobs[job_id].current_version
        raise ValueError(f"Job {job_id} not found")


class MockSchemaCollector(SchemaCollector):
    """Mock implementation of SchemaCollector for testing."""

    def __init__(self):
        self.schemas: dict[tuple[str, str], dict] = {
            ("test_program", "test_core"): {
                "properties": {
                    "field1": {"type": "string", "required": True},
                    "field2": {"type": "string", "enum": ["option1", "option2"]},
                    "field3": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                }
            }
        }
        self.columns: dict[tuple[str, str], list[str]] = {("test_program", "test_core"): ["field1", "field2", "field3"]}
        self.validation_rules: dict[tuple[str, str], dict] = {
            ("test_program", "test_core"): {
                "field1": {"required": True},
                "field2": {"required": False, "options": ["option1", "option2"]},
                "field3": {"required": False, "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            }
        }

    async def get_available_schemas(self) -> list[SchemaInfo]:
        return [
            SchemaInfo(
                core_uuid="test_core",
                core_name="Test Core",
                core_path="test_core.json",
                program_uuid="test_program",
                program_name="Test Program",
                program_path="test_program.json",
            )
        ]

    async def get_schema(self, program_id: str, core_id: str) -> dict:
        return self.schemas.get((program_id, core_id), {})

    async def get_schema_columns(self, program_id: str, core_id: str) -> list[str]:
        return self.columns.get((program_id, core_id), [])

    async def get_validation_rules(self, program_id: str, core_id: str) -> dict:
        return self.validation_rules.get((program_id, core_id), {})


@pytest.fixture
def mock_job_status_saver():
    """Fixture providing a mock JobStatusSaver."""
    return MockJobStatusSaver()


@pytest.fixture
def mock_schema_collector():
    """Fixture providing a mock SchemaCollector."""
    return MockSchemaCollector()


@pytest.fixture
def sample_config():
    """Fixture providing a sample configuration."""
    return {
        "aws_region": "us-east-1",
        "schema_directory": "/tmp/schemas",
        "session_saver_type": "file",
        "file_session_directory": "/tmp/sessions",
        "enable_redis_cache": False,
        "enable_memory_cache": True,
        "embedding_provider": "bedrock",
        "job_status_saver_type": "local",
        "job_status_storage_dir": "/tmp/job_status",
        "result_saver_type": "local",
        "results_local_dir": "/tmp/results",
    }


@pytest.fixture
def sample_dataframe():
    """Fixture providing a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "field1": ["value1", "", "value3"],
            "field2": ["option1", "invalid_option", "option2"],
            "field3": ["2023-01-01", "invalid_date", "2023-12-31"],
        }
    )


class TestMetadataHarmonizationProcessorInitialization:
    """Test processor initialization and configuration."""

    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    def test_init_with_configuration_driven_components(self, mock_path, sample_config):
        """Test successful initialization with configuration-driven components."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        # Add data saver configuration
        config_data = {
            **sample_config,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "local",
            "results_local_dir": "/tmp/results",
        }

        config = ProcessorConfig(**config_data)
        processor = MetadataHarmonizationProcessor(config=config, session_id="test-session-123")

        assert processor.data_saver is not None
        assert processor.schema_collector is not None
        assert processor.session_id == "test-session-123"
        assert isinstance(processor.config, ProcessorConfig)
        assert processor.config.aws_region == "us-east-1"
        assert processor.session_manager is not None
        assert processor.processing_graph is not None

    def test_init_missing_config(self):
        """Test initialization fails without config."""
        with pytest.raises(ValueError, match="config is required"):
            MetadataHarmonizationProcessor(config=None, session_id="test-session")

    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    def test_init_missing_session_id(self, mock_path, sample_config):
        """Test initialization fails without session_id."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config_data = {
            **sample_config,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "local",
            "results_local_dir": "/tmp/results",
        }
        config = ProcessorConfig(**config_data)
        with pytest.raises(ValueError, match="session_id is required"):
            MetadataHarmonizationProcessor(config=config, session_id="")

    @patch("metadata_harmonization_processor.processor.S3SessionManager")
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    def test_init_with_s3_session_config(self, mock_path, mock_s3_session_manager):
        """Test initialization with S3 session configuration."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config_data = {
            "aws_region": "us-west-2",
            "schema_directory": "/tmp/schemas",
            "session_saver_type": "s3",
            "session_s3_bucket": "test-bucket",
            "session_s3_prefix": "test-prefix/",
            "enable_redis_cache": False,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "local",
            "results_local_dir": "/tmp/results",
        }

        # Mock S3SessionManager to avoid AWS credential issues
        mock_session_manager_instance = MagicMock()
        mock_s3_session_manager.return_value = mock_session_manager_instance

        config = ProcessorConfig(**config_data)
        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session-s3",
            session_config={"bucket": "custom-bucket"},
        )

        assert processor.config.session_saver_type == "s3"
        assert processor.session_manager is not None

        # Verify S3SessionManager was called with correct parameters
        mock_s3_session_manager.assert_called_once_with(
            session_id="test-session-s3",
            bucket="custom-bucket",
            prefix="test-prefix/",
            region_name="us-west-2",
        )


class TestSchemaIdManagement:
    """Test schema ID setting and validation."""


class TestProcessingPipeline:
    """Test the main processing pipeline."""

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_success_configuration_driven(self, mock_path, sample_dataframe):
        """Test successful processing pipeline execution with configuration-driven DataSaver."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        # Mock the Graph.invoke_async method to simulate successful processing
        with patch("strands.multiagent.graph.Graph.invoke_async") as mock_graph_execute:
            # Set up mock validation results
            mock_validation_results = ValidationResults(
                validation_results=[],
                summary=ValidationResultsSummary(
                    total_rows=3,
                    total_errors=0,
                    error_types={},
                    columns_validated=3,
                ),
            )

            # Mock MultiAgentResult structure
            from strands.multiagent.base import Status

            # Create a callback to update processor state when invoke_async is called
            async def mock_invoke_async(*args, **kwargs):
                # Extract the processor_state from invocation_state
                invocation_state = kwargs.get("invocation_state", {})
                processor_state = invocation_state.get("processor_state")

                # Update the processor state in-place with our mock data
                if processor_state:
                    processor_state.aligned_df = sample_dataframe
                    # Create CombinedResults with validation results
                    processor_state.combined_results = CombinedResults(validation_results=mock_validation_results)

                # Return a mock result
                mock_result = MagicMock()
                mock_result.status = Status.COMPLETED
                mock_result.results = {}
                return mock_result

            mock_graph_execute.side_effect = mock_invoke_async

            # Create processor with configuration-driven approach
            config_data = {
                "aws_region": "us-east-1",
                "schema_directory": "/tmp/schemas",
                "session_saver_type": "file",
                "file_session_directory": "/tmp/sessions",
                "enable_redis_cache": False,
                "job_status_saver_type": "local",
                "job_status_storage_dir": "/tmp/job_status",
                "result_saver_type": "local",
                "results_local_dir": "/tmp/results",
            }
            config = ProcessorConfig(**config_data)

            processor = MetadataHarmonizationProcessor(config=config, session_id="test-session")

            # Mock the DataSaver methods to avoid file system operations
            with (
                patch.object(processor.data_saver, "update_job_status") as mock_update_status,
                patch.object(processor.data_saver, "save_job_and_results") as mock_save_results,
            ):
                mock_save_results.return_value = MagicMock()

                # Execute processing
                result = await processor.process(sample_dataframe, "test_program", "test_core")

                # Verify results - processor now returns CombinedResults
                assert isinstance(result, CombinedResults)
                assert result.has_validation_results()
                assert result.validation_results.summary.total_rows == 3

                # Verify graph was executed
                mock_graph_execute.assert_called_once()

                # Verify DataSaver methods were called
                mock_update_status.assert_called()
                mock_save_results.assert_called_once()

                # Verify final state was stored
                assert processor.get_current_state() is not None

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_empty_dataframe(self, mock_path, sample_config):
        """Test processing fails with empty DataFrame."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config = ProcessorConfig(**sample_config)

        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session",
        )

        with pytest.raises(ValueError, match="metadata_df cannot be None or empty"):
            await processor.process(pd.DataFrame(), "test_program", "test_core")

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_none_dataframe(self, mock_path, sample_config):
        """Test processing fails with None DataFrame."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config = ProcessorConfig(**sample_config)

        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session",
        )

        with pytest.raises(ValueError, match="metadata_df cannot be None or empty"):
            await processor.process(None, "test_program", "test_core")

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_empty_program_id(
        self,
        mock_path,
        sample_config,
        sample_dataframe,
    ):
        """Test processing fails with empty program_id."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config = ProcessorConfig(**sample_config)

        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session",
        )

        with pytest.raises(ValueError, match="program_id cannot be empty"):
            await processor.process(sample_dataframe, "", "test_core")

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_empty_core_id(
        self,
        mock_path,
        sample_config,
        sample_dataframe,
    ):
        """Test processing fails with empty core_id."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config = ProcessorConfig(**sample_config)

        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session",
        )

        with pytest.raises(ValueError, match="core_id cannot be empty"):
            await processor.process(sample_dataframe, "test_program", "")

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    async def test_process_graph_execution_error(
        self,
        mock_path,
        sample_config,
        sample_dataframe,
    ):
        """Test processing handles MultiAgentBase graph execution errors."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        # Mock the Graph.invoke_async method to simulate processing failure
        with patch("strands.multiagent.graph.Graph.invoke_async") as mock_graph_execute:
            mock_graph_execute.side_effect = Exception("MultiAgentBase graph execution failed")

            # Create processor
            config = ProcessorConfig(**sample_config)

            processor = MetadataHarmonizationProcessor(
                config=config,
                session_id="test-session",
            )

            # The processor catches and wraps the exception
            with pytest.raises((ProcessingError, Exception)):
                await processor.process(sample_dataframe, "test_program", "test_core")


class TestStateManagement:
    """Test processor state management."""


class TestJobStatusTracking:
    """Test job status and progress tracking."""


class TestErrorHandling:
    """Test error handling and recovery."""


class TestCleanup:
    """Test resource cleanup."""


class TestStringRepresentations:
    """Test string representations of the processor."""


class TestConfigurationDrivenDataSaver:
    """Test configuration-driven DataSaver creation."""

    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    def test_create_data_saver_local_configuration(self, mock_path):
        """Test DataSaver creation with local configuration."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config_data = {
            "aws_region": "us-east-1",
            "schema_directory": "/tmp/schemas",
            "session_saver_type": "file",
            "file_session_directory": "/tmp/sessions",
            "enable_redis_cache": False,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "local",
            "results_local_dir": "/tmp/results",
        }

        config = ProcessorConfig(**config_data)
        processor = MetadataHarmonizationProcessor(config=config, session_id="test-session")

        # Verify DataSaver was created
        assert processor.data_saver is not None

        # Verify correct implementations were created
        from metadata_harmonization_processor.implementations.local_job_status_saver import (
            LocalJobStatusSaver,
        )
        from metadata_harmonization_processor.implementations.local_result_saver import (
            LocalResultSaver,
        )

        assert isinstance(processor.data_saver.job_status_saver, LocalJobStatusSaver)
        assert isinstance(processor.data_saver.result_saver, LocalResultSaver)

    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    @patch("metadata_harmonization_processor.implementations.dynamodb_job_status_saver.boto3")
    @patch("metadata_harmonization_processor.implementations.s3_result_saver.boto3")
    def test_create_data_saver_aws_configuration(self, mock_s3_boto3, mock_dynamodb_boto3, mock_path):
        """Test DataSaver creation with AWS configuration."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        # Mock boto3 to avoid AWS credential issues
        mock_s3_client = MagicMock()
        mock_s3_client.list_buckets.return_value = {}
        mock_s3_boto3.client.return_value = mock_s3_client

        mock_dynamodb_resource = MagicMock()
        mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource

        config_data = {
            "aws_region": "us-east-1",
            "schema_directory": "/tmp/schemas",
            "session_saver_type": "file",
            "file_session_directory": "/tmp/sessions",
            "enable_redis_cache": False,
            "job_status_saver_type": "dynamodb",
            "job_status_table_name": "test-table",
            "result_saver_type": "s3",
            "results_s3_bucket": "test-bucket",
            "results_s3_prefix": "test-prefix/",
        }

        config = ProcessorConfig(**config_data)
        processor = MetadataHarmonizationProcessor(config=config, session_id="test-session")

        # Verify DataSaver was created
        assert processor.data_saver is not None

        # Verify correct implementations were created
        from metadata_harmonization_processor.implementations.dynamodb_job_status_saver import (
            DynamodbJobStatusSaver,
        )
        from metadata_harmonization_processor.implementations.s3_result_saver import (
            S3ResultSaver,
        )

        assert isinstance(processor.data_saver.job_status_saver, DynamodbJobStatusSaver)
        assert isinstance(processor.data_saver.result_saver, S3ResultSaver)

    @patch("metadata_harmonization_processor.implementations.file_schema_collector.Path")
    def test_create_schema_collector_from_config(self, mock_path):
        """Test SchemaCollector creation from configuration."""
        # Mock schema directory to exist
        mock_schema_dir = MagicMock()
        mock_schema_dir.exists.return_value = True
        mock_catalog_path = MagicMock()
        mock_catalog_path.exists.return_value = True
        mock_path.return_value = mock_schema_dir
        mock_schema_dir.__truediv__ = MagicMock(return_value=mock_catalog_path)

        config_data = {
            "aws_region": "us-east-1",
            "schema_directory": "/tmp/schemas",
            "session_saver_type": "file",
            "file_session_directory": "/tmp/sessions",
            "enable_redis_cache": False,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "local",
            "results_local_dir": "/tmp/results",
        }

        config = ProcessorConfig(**config_data)
        processor = MetadataHarmonizationProcessor(config=config, session_id="test-session")

        # Verify SchemaCollector was created
        assert processor.schema_collector is not None

        # Verify correct implementation was created
        from metadata_harmonization_processor.implementations.file_schema_collector import (
            FileBasedSchemaCollector,
        )

        assert isinstance(processor.schema_collector, FileBasedSchemaCollector)

    def test_missing_s3_bucket_configuration(self):
        """Test that missing S3 bucket configuration raises error."""
        config_data = {
            "aws_region": "us-east-1",
            "schema_directory": "/tmp/schemas",
            "session_saver_type": "file",
            "file_session_directory": "/tmp/sessions",
            "enable_redis_cache": False,
            "job_status_saver_type": "local",
            "job_status_storage_dir": "/tmp/job_status",
            "result_saver_type": "s3",
            "results_s3_bucket": None,  # Missing required bucket
            "results_s3_prefix": "test-prefix/",
        }

        # This should fail at config validation level
        with pytest.raises(
            ValueError,
            match="results_s3_bucket is required when result_saver_type is 's3'",
        ):
            ProcessorConfig(**config_data)


class TestStrandsGraphIntegration:
    """Test AWS Strands graph integration."""
