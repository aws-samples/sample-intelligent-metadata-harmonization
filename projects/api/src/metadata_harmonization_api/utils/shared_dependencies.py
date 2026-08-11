# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Shared dependency injection system for API and MCP server integration.

This module provides centralized dependency management functions that allow
both REST API endpoints and MCP server tools to use the same component instances.
Uses caching for singleton instances where appropriate to ensure resource efficiency.
"""

import logging
from functools import lru_cache
from typing import Optional

from metadata_harmonization_processor.implementations.file_schema_collector import FileBasedSchemaCollector
from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.implementations.dynamodb_job_status_saver import DynamodbJobStatusSaver
from metadata_harmonization_processor.implementations.local_job_status_saver import LocalJobStatusSaver
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_api.clients import DynamoDbManager
from metadata_harmonization_api.workers.metadata_worker import MetadataWorker

logger = logging.getLogger(__name__)


# Global cache for non-hashable objects - keyed by schema directory
_schema_collector_cache: dict[str, FileBasedSchemaCollector] = {}
_processor_manager_cache: Optional[ProcessorManager] = None
_job_status_saver_cache: Optional[JobStatusSaver] = None


def get_schema_collector(processor_config: ProcessorConfig) -> FileBasedSchemaCollector:
    """
    Get shared SchemaCollector instance.

    This function provides a cached singleton instance of SchemaCollector
    that can be used by both REST API endpoints and MCP server tools.
    Different schema directories get different instances.

    Args:
        processor_config: ProcessorConfig instance for schema collector initialization

    Returns:
        Cached SchemaCollector instance for the given schema directory
    """
    global _schema_collector_cache

    schema_dir = processor_config.schema_directory
    logger.info(f"Requesting schema collector for directory: {schema_dir}")

    if schema_dir not in _schema_collector_cache:
        try:
            logger.info(f"Creating new shared FileBasedSchemaCollector instance for {schema_dir}")
            _schema_collector_cache[schema_dir] = FileBasedSchemaCollector(schema_dir)
            logger.info(f"Successfully created schema collector for {schema_dir}")
        except Exception as e:
            logger.error(f"Failed to create schema collector for {schema_dir}: {e}")
            logger.exception("Schema collector creation exception details:")
            raise
    else:
        logger.debug(f"Retrieving cached FileBasedSchemaCollector instance for {schema_dir}")

    return _schema_collector_cache[schema_dir]


def get_processor_manager(processor_config: ProcessorConfig) -> ProcessorManager:
    """
    Get shared ProcessorManager instance.

    This function provides a cached singleton instance of ProcessorManager
    that manages processor lifecycle for both REST API and MCP server operations.

    Args:
        processor_config: ProcessorConfig instance for processor manager initialization

    Returns:
        Cached ProcessorManager instance
    """
    global _processor_manager_cache

    if _processor_manager_cache is None:
        try:
            logger.info("Creating new shared ProcessorManager instance")
            _processor_manager_cache = ProcessorManager(processor_config)
            logger.info("Successfully created ProcessorManager instance")
        except Exception as e:
            logger.error(f"Failed to create ProcessorManager: {e}")
            logger.exception("ProcessorManager creation exception details:")
            raise
    else:
        logger.debug("Retrieving cached ProcessorManager instance")

    return _processor_manager_cache


@lru_cache(maxsize=1)
def get_ddb_manager() -> DynamoDbManager:
    """
    Get shared DynamoDB manager instance.

    This function provides a cached singleton instance of DynamoDbManager
    for database operations shared between REST API and MCP server.

    Returns:
        Cached DynamoDbManager instance
    """
    logger.debug("Creating/retrieving shared DynamoDbManager instance")
    return DynamoDbManager()


def get_job_status_saver(processor_config: ProcessorConfig) -> JobStatusSaver:
    """
    Get shared JobStatusSaver instance.

    This function provides a cached singleton instance of JobStatusSaver
    that can be used by both REST API endpoints and MCP server tools.

    Args:
        processor_config: ProcessorConfig instance for job status saver initialization

    Returns:
        Cached JobStatusSaver instance
    """
    global _job_status_saver_cache

    if _job_status_saver_cache is None:
        try:
            logger.info(
                f"Creating new shared JobStatusSaver instance of type: {processor_config.job_status_saver_type}"
            )

            if processor_config.job_status_saver_type == "dynamodb":
                logger.info(
                    f"Initializing DynamoDB job status saver with table: {processor_config.job_status_table_name}"
                )
                _job_status_saver_cache = DynamodbJobStatusSaver(table_name=processor_config.job_status_table_name)
            else:
                # Use local job status saver for development
                logger.info(
                    f"Initializing local job status saver with directory: {processor_config.job_status_storage_dir}"
                )
                _job_status_saver_cache = LocalJobStatusSaver(
                    storage_type="file", storage_dir=processor_config.job_status_storage_dir
                )

            logger.info("Successfully created JobStatusSaver instance")
        except Exception as e:
            logger.error(f"Failed to create JobStatusSaver: {e}")
            logger.exception("JobStatusSaver creation exception details:")
            raise
    else:
        logger.debug("Retrieving cached JobStatusSaver instance")

    return _job_status_saver_cache


def get_metadata_worker(processor_manager: ProcessorManager) -> MetadataWorker:
    """
    Get MetadataWorker instance.

    MetadataWorker is not cached as it's stateless and lightweight.
    Each call creates a new instance that uses the shared ProcessorManager.

    Args:
        processor_manager: ProcessorManager instance for worker initialization

    Returns:
        New MetadataWorker instance using shared ProcessorManager
    """
    logger.debug("Creating new MetadataWorker instance with shared ProcessorManager")
    return MetadataWorker(processor_manager)


def clear_dependency_cache() -> None:
    """
    Clear all cached dependencies.

    This function clears both global cache variables and LRU cache for all singleton instances.
    Useful for testing or when configuration changes require fresh instances.
    """
    global _schema_collector_cache, _processor_manager_cache, _job_status_saver_cache

    logger.info("Clearing shared dependency cache")
    _schema_collector_cache.clear()
    _processor_manager_cache = None
    _job_status_saver_cache = None
    get_ddb_manager.cache_clear()


def get_cache_info() -> dict:
    """
    Get cache information for all cached dependencies.

    Returns:
        Dictionary containing cache statistics for each cached function
    """
    global _schema_collector_cache, _processor_manager_cache, _job_status_saver_cache

    return {
        "schema_collector": {
            "cached_instances": len(_schema_collector_cache),
            "schema_directories": list(_schema_collector_cache.keys()),
        },
        "processor_manager": {"cached": _processor_manager_cache is not None},
        "job_status_saver": {"cached": _job_status_saver_cache is not None},
        "ddb_manager": get_ddb_manager.cache_info()._asdict(),
    }


# Convenience function for getting all core dependencies at once
def get_core_dependencies(
    processor_config: ProcessorConfig,
) -> tuple[FileBasedSchemaCollector, ProcessorManager, DynamoDbManager, JobStatusSaver, MetadataWorker]:
    """
    Get all core dependencies in a single call.

    This convenience function retrieves all the main shared dependencies
    that are commonly used together by both REST API and MCP server components.

    Args:
        processor_config: ProcessorConfig instance for initialization

    Returns:
        Tuple containing (schema_collector, processor_manager, ddb_manager, job_status_saver, metadata_worker)
    """
    logger.debug("Retrieving all core shared dependencies")

    schema_collector = get_schema_collector(processor_config)
    processor_manager = get_processor_manager(processor_config)
    ddb_manager = get_ddb_manager()
    job_status_saver = get_job_status_saver(processor_config)
    metadata_worker = get_metadata_worker(processor_manager)

    return schema_collector, processor_manager, ddb_manager, job_status_saver, metadata_worker
