# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Processor Manager for API integration with metadata-harmonization-processor package.

This module provides the ProcessorManager class that manages MetadataHarmonizationProcessor
instances, handles processor lifecycle, session management, and configuration loading.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Any

import pandas as pd
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import ProcessorConfig, load_processor_settings
from metadata_harmonization_processor.utils.data_loader import load_metadata_csv
from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector

logger = logging.getLogger(__name__)


class ProcessorManager:
    """
    Manages MetadataHarmonizationProcessor instances for the API.

    Provides processor lifecycle management, session handling, and configuration
    loading from API config.yaml. Supports both local and cloud environments
    with automatic backend selection.
    """

    def __init__(self, processor_config: ProcessorConfig):
        """
        Initialize ProcessorManager with processor configuration.

        Args:
            processor_config: Configuration for the metadata harmonization processor
        """
        self.processor_config = processor_config
        self._processors: Dict[str, MetadataHarmonizationProcessor] = {}
        self._lock = asyncio.Lock()

        logger.info(f"ProcessorManager initialized with config: {processor_config.model_dump()}")

    async def get_processor(self, session_id: str) -> MetadataHarmonizationProcessor:
        """
        Get or create a processor instance for a session.

        Args:
            session_id: Session/job identifier used to cache and retrieve processors

        Returns:
            MetadataHarmonizationProcessor instance for the session
        """
        async with self._lock:
            if session_id in self._processors:
                logger.debug(f"Reusing existing processor for session: {session_id}")
                return self._processors[session_id]

            logger.debug(f"Creating new processor instance for session: {session_id}")

            processor = MetadataHarmonizationProcessor(config=self.processor_config, session_id=session_id)

            self._processors[session_id] = processor
            logger.info(f"Created processor instance for session: {session_id}")

            return processor

    async def cleanup_processor(self, session_id: str) -> None:
        """
        Clean up processor resources for a session.

        Args:
            session_id: Session identifier of the processor to clean up
        """
        async with self._lock:
            await self._cleanup_processor_unlocked(session_id)

    async def _cleanup_processor_unlocked(self, session_id: str) -> None:
        """
        Internal cleanup without acquiring the lock.

        Must be called while self._lock is already held.
        """
        processor = self._processors.pop(session_id, None)
        if processor is not None:
            try:
                if hasattr(processor, "cleanup"):
                    await processor.cleanup()
            except Exception as e:
                logger.warning(f"Error during processor cleanup for session {session_id}: {e}")
            logger.info(f"Cleaned up processor instance for session: {session_id}")

    async def cleanup_all_processors(self) -> None:
        """Clean up all processor instances."""
        async with self._lock:
            session_ids = list(self._processors.keys())
            for session_id in session_ids:
                await self._cleanup_processor_unlocked(session_id)
            logger.info("Cleaned up all processor instances")

    def get_active_session_count(self) -> int:
        """
        Get the number of active processor sessions.

        Returns:
            Number of active processor instances
        """
        return len(self._processors)

    def get_active_sessions(self) -> list[str]:
        """
        Get list of active session IDs.

        Returns:
            List of active session identifiers
        """
        return list(self._processors.keys())

    async def load_metadata_csv(self, file_path: str, program_id: str, core_id: str) -> pd.DataFrame:
        """
        Load a CSV file with schema-aware dtype mapping.

        This method provides convenient access to schema-aware CSV loading
        for API endpoints, using the processor configuration's schema collector.

        Args:
            file_path: Path to the CSV file to load
            program_id: Schema program UUID
            core_id: Schema core UUID

        Returns:
            DataFrame with dtypes matching the schema definition

        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If schema cannot be loaded

        Example:
            >>> processor_manager = ProcessorManager(config)
            >>> df = await processor_manager.load_metadata_csv(
            ...     "data.csv",
            ...     program_id="eb7cb69f-04e5-5a60-930a-e92a4e1d23d0",
            ...     core_id="9495afdb-7e59-5e2b-97a6-45d72c13a5c5"
            ... )
        """
        # Create schema collector from processor config
        schema_collector = FileBasedSchemaCollector(self.processor_config.schema_directory)

        logger.info(f"Loading CSV with schema-aware types: {file_path}")
        df = await load_metadata_csv(file_path, program_id, core_id, schema_collector)
        logger.info(f"Loaded {len(df)} rows with {len(df.columns)} columns")

        return df


def create_processor_manager_from_config(
    config_path: Optional[Path] = None, environment_overrides: Optional[Dict[str, Any]] = None
) -> ProcessorManager:
    """
    Create ProcessorManager from configuration file with environment overrides.

    Args:
        config_path: Path to processor configuration YAML file
        environment_overrides: Environment-specific configuration overrides

    Returns:
        Configured ProcessorManager instance

    Raises:
        FileNotFoundError: If config_path is provided but file doesn't exist
        ValueError: If configuration validation fails
    """
    if environment_overrides is None:
        environment_overrides = {}

    logger.info(f"Loading processor configuration from: {config_path}")
    logger.debug(f"Environment overrides: {environment_overrides}")

    try:
        processor_config = load_processor_settings(config_path=config_path, override=environment_overrides)

        logger.info("Successfully loaded processor configuration")
        return ProcessorManager(processor_config)

    except Exception as e:
        logger.error(f"Failed to create ProcessorManager: {e}")
        raise


def detect_environment_overrides() -> Dict[str, Any]:
    """
    Detect environment and create appropriate configuration overrides.

    This function checks environment variables to determine if we're running
    in local or cloud mode and returns appropriate configuration overrides.

    Returns:
        Dictionary of configuration overrides based on environment detection
    """
    import os

    overrides = {}

    # Check if we're in cloud environment
    environment = os.getenv("PROCESSOR_ENVIRONMENT", "local")

    if environment == "cloud":
        logger.info("Detected cloud environment, applying cloud configuration overrides")

        # Cloud storage configuration
        overrides.update({"job_status_saver_type": "dynamodb", "result_saver_type": "s3", "session_type": "s3"})

        # Apply specific environment variable overrides
        env_mappings = {
            "PROCESSOR_JOB_STATUS_TABLE_NAME": "job_status_table_name",
            "PROCESSOR_RESULTS_S3_BUCKET": "results_s3_bucket",
            "PROCESSOR_RESULTS_S3_PREFIX": "results_s3_prefix",
            "PROCESSOR_S3_BUCKET": "s3_bucket",
            "PROCESSOR_S3_PREFIX": "s3_prefix",
            "PROCESSOR_AWS_REGION": "aws_region",
            "PROCESSOR_AWS_PROFILE": "aws_profile",
            "PROCESSOR_REDIS_ENDPOINT": "redis_endpoint",
            "PROCESSOR_REDIS_PORT": "redis_port",
            "PROCESSOR_ENABLE_REDIS_CACHE": "enable_redis_cache",
            "PROCESSOR_BEDROCK_MODEL_ID": "bedrock_model_id",
            "PROCESSOR_EMBEDDING_PROVIDER": "embedding_provider",
            "PROCESSOR_SAGEMAKER_ENDPOINT_NAME": "sagemaker_endpoint_name",
            "PROCESSOR_COSINE_SIMILARITY_THRESHOLD": "cosine_similarity_threshold",
        }

        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert boolean strings
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                # Convert numeric strings
                elif value.isdigit():
                    value = int(value)
                elif "." in value and value.replace(".", "").isdigit():
                    value = float(value)

                overrides[config_key] = value

    else:
        logger.info("Detected local environment, applying local configuration overrides")

        # Local development configuration
        overrides.update(
            {
                "job_status_saver_type": "local",
                "result_saver_type": "local",
                "session_type": "file",
                "local_development_mode": True,
                "enable_redis_cache": False,
                "enable_memory_cache": True,
            }
        )

    logger.debug(f"Environment overrides: {overrides}")
    return overrides
