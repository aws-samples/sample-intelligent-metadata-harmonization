# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for ProcessorManager and related factory functions."""

import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

from metadata_harmonization_api.services.processor_manager import ProcessorManager, create_processor_manager_from_config
from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor import MetadataHarmonizationProcessor


class TestProcessorManagerFactory:
    """Test cases for ProcessorManager factory functions."""

    def test_create_processor_manager_from_config_with_file(self):
        """Test creating ProcessorManager from configuration file."""
        config_data = {
            "schema_directory": "./test_schemas",
            "local_development_mode": True,
            "job_status_saver_type": "local",
            "result_saver_type": "local",
            "session_saver_type": "file",
            "file_session_directory": "./test_sessions",
            "enable_redis_cache": False,
            "enable_memory_cache": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with patch("metadata_harmonization_api.services.processor_manager.load_processor_settings") as mock_load:
                mock_config = ProcessorConfig(**config_data)
                mock_load.return_value = mock_config

                manager = create_processor_manager_from_config(
                    config_path=config_path, environment_overrides={"enable_redis_cache": False}
                )

                assert isinstance(manager, ProcessorManager)
                assert manager.processor_config == mock_config

                # Verify load_processor_settings was called correctly
                mock_load.assert_called_once_with(config_path=config_path, override={"enable_redis_cache": False})
        finally:
            config_path.unlink()

    def test_create_processor_manager_from_config_no_file(self):
        """Test creating ProcessorManager without configuration file."""
        with patch("metadata_harmonization_api.services.processor_manager.load_processor_settings") as mock_load:
            mock_config = ProcessorConfig(
                schema_directory="./schemas",
                local_development_mode=True,
                job_status_saver_type="local",
                result_saver_type="local",
                session_saver_type="file",
                file_session_directory="./test_sessions",
                enable_redis_cache=False,
                enable_memory_cache=True,
            )
            mock_load.return_value = mock_config

            manager = create_processor_manager_from_config(
                config_path=None, environment_overrides={"job_status_saver_type": "local"}
            )

            assert isinstance(manager, ProcessorManager)
            mock_load.assert_called_once_with(config_path=None, override={"job_status_saver_type": "local"})

    def test_create_processor_manager_from_config_invalid_config(self):
        """Test creating ProcessorManager with invalid configuration."""
        with patch("metadata_harmonization_api.services.processor_manager.load_processor_settings") as mock_load:
            mock_load.side_effect = ValueError("Invalid configuration")

            with pytest.raises(ValueError, match="Invalid configuration"):
                create_processor_manager_from_config()

    def test_create_processor_manager_from_config_file_not_found(self):
        """Test creating ProcessorManager with non-existent config file."""
        nonexistent_path = Path("/nonexistent/config.yaml")

        with patch("metadata_harmonization_api.services.processor_manager.load_processor_settings") as mock_load:
            mock_load.side_effect = FileNotFoundError("Config file not found")

            with pytest.raises(FileNotFoundError):
                create_processor_manager_from_config(config_path=nonexistent_path)


class TestProcessorManagerLifecycle:
    """Test cases for ProcessorManager lifecycle management."""

    @pytest.fixture
    def processor_config(self):
        """Create a test processor configuration."""
        return ProcessorConfig(
            schema_directory="./test_schemas",
            local_development_mode=True,
            job_status_saver_type="local",
            result_saver_type="local",
            session_saver_type="file",
            file_session_directory="./test_sessions",
            enable_redis_cache=False,
            enable_memory_cache=True,
        )

    @pytest.fixture
    def processor_manager(self, processor_config):
        """Create a ProcessorManager instance."""
        return ProcessorManager(processor_config)

    @pytest.mark.asyncio
    async def test_processor_manager_initialization(self, processor_config):
        """Test ProcessorManager initialization."""
        manager = ProcessorManager(processor_config)

        assert manager.processor_config == processor_config
        assert manager.get_active_session_count() == 0
        assert manager.get_active_sessions() == []

    @pytest.mark.asyncio
    async def test_get_processor_creates_new_instance(self, processor_manager):
        """Test that get_processor creates new processor instances."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_class.return_value = mock_processor_instance

            processor = await processor_manager.get_processor(session_id)

            assert processor == mock_processor_instance
            assert processor_manager.get_active_session_count() == 1
            assert session_id in processor_manager.get_active_sessions()

            # Verify processor was created with correct parameters
            mock_processor_class.assert_called_once_with(
                config=processor_manager.processor_config, session_id=session_id
            )

    @pytest.mark.asyncio
    async def test_get_processor_reuses_existing_instance(self, processor_manager):
        """Test that get_processor reuses existing processor instances."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_class.return_value = mock_processor_instance

            # Get processor twice
            processor1 = await processor_manager.get_processor(session_id)
            processor2 = await processor_manager.get_processor(session_id)

            # Should be the same instance
            assert processor1 == processor2
            assert processor_manager.get_active_session_count() == 1

            # Should only create processor once
            mock_processor_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_processor_multiple_sessions(self, processor_manager):
        """Test managing multiple processor sessions."""
        session_ids = ["session_1", "session_2", "session_3"]

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_class.return_value = mock_processor_instance

            processors = []
            for session_id in session_ids:
                processor = await processor_manager.get_processor(session_id)
                processors.append(processor)

            assert processor_manager.get_active_session_count() == 3
            assert set(processor_manager.get_active_sessions()) == set(session_ids)

            # Each session should have its own processor instance
            assert mock_processor_class.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_processor_removes_session(self, processor_manager):
        """Test that cleanup_processor removes processor from cache."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_instance.cleanup = AsyncMock()
            mock_processor_class.return_value = mock_processor_instance

            # Create processor
            await processor_manager.get_processor(session_id)
            assert processor_manager.get_active_session_count() == 1

            # Clean up processor
            await processor_manager.cleanup_processor(session_id)

            assert processor_manager.get_active_session_count() == 0
            assert session_id not in processor_manager.get_active_sessions()

            # Verify cleanup was called if method exists
            if hasattr(mock_processor_instance, "cleanup"):
                mock_processor_instance.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_processor_nonexistent_session(self, processor_manager):
        """Test cleanup_processor with non-existent session ID."""
        # Should not raise an error
        await processor_manager.cleanup_processor("nonexistent_session")
        assert processor_manager.get_active_session_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_processors(self, processor_manager):
        """Test cleaning up all processor instances."""
        session_ids = ["session_1", "session_2", "session_3"]

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_class.return_value = mock_processor_instance

            # Create multiple processors
            for session_id in session_ids:
                await processor_manager.get_processor(session_id)

            assert processor_manager.get_active_session_count() == 3

            # Clean up all processors
            await processor_manager.cleanup_all_processors()

            assert processor_manager.get_active_session_count() == 0
            assert processor_manager.get_active_sessions() == []

    @pytest.mark.asyncio
    async def test_processor_manager_thread_safety(self, processor_manager):
        """Test that ProcessorManager operations are thread-safe."""
        import asyncio

        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_class.return_value = mock_processor_instance

            # Simulate concurrent access to the same session
            async def get_processor_task():
                return await processor_manager.get_processor(session_id)

            # Run multiple concurrent tasks
            tasks = [get_processor_task() for _ in range(5)]
            processors = await asyncio.gather(*tasks)

            # All should return the same processor instance
            assert all(p == processors[0] for p in processors)
            assert processor_manager.get_active_session_count() == 1

            # Should only create processor once despite concurrent access
            mock_processor_class.assert_called_once()


class TestProcessorManagerErrorHandling:
    """Test cases for ProcessorManager error handling."""

    @pytest.fixture
    def processor_config(self):
        """Create a test processor configuration."""
        return ProcessorConfig(
            schema_directory="./test_schemas",
            local_development_mode=True,
            job_status_saver_type="local",
            result_saver_type="local",
            session_saver_type="file",
            file_session_directory="./test_sessions",
            enable_redis_cache=False,
            enable_memory_cache=True,
        )

    @pytest.fixture
    def processor_manager(self, processor_config):
        """Create a ProcessorManager instance."""
        return ProcessorManager(processor_config)

    @pytest.mark.asyncio
    async def test_get_processor_creation_error(self, processor_manager):
        """Test handling of processor creation errors."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_class.side_effect = Exception("Processor creation failed")

            with pytest.raises(Exception, match="Processor creation failed"):
                await processor_manager.get_processor(session_id)

            # Should not cache failed processor
            assert processor_manager.get_active_session_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_processor_with_cleanup_error(self, processor_manager):
        """Test cleanup_processor when processor cleanup method fails."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock(spec=MetadataHarmonizationProcessor)
            mock_processor_instance.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
            mock_processor_class.return_value = mock_processor_instance

            # Create processor
            await processor_manager.get_processor(session_id)

            # Cleanup should handle the error gracefully
            await processor_manager.cleanup_processor(session_id)

            # Processor should still be removed from cache despite cleanup error
            assert processor_manager.get_active_session_count() == 0


class TestProcessorManagerStateRetrieval:
    """Test cases for ProcessorManager state retrieval functionality."""

    @pytest.fixture
    def processor_config(self):
        """Create a test processor configuration."""
        return ProcessorConfig(
            schema_directory="./test_schemas",
            local_development_mode=True,
            job_status_saver_type="local",
            result_saver_type="local",
            session_saver_type="file",
            file_session_directory="./test_sessions",
            s3_bucket="test-bucket",  # Required even for file session type due to validation
            enable_redis_cache=False,
            enable_memory_cache=True,
        )

    @pytest.fixture
    def processor_manager(self, processor_config):
        """Create a ProcessorManager instance."""
        return ProcessorManager(processor_config)
