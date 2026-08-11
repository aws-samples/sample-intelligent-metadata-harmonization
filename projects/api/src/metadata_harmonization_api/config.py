# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Clean configuration for metadata API."""

import os
import yaml
from pathlib import Path
from typing import Any, Optional, Tuple, List
from loguru import logger

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings

from metadata_harmonization_api.models import LogLevel

# Import processor configuration
from metadata_harmonization_processor.config import ProcessorConfig, deep_merge_dicts


class AwsConfig(BaseSettings):
    """AWS configuration."""

    model_config = ConfigDict(extra="allow")

    region: str = Field(
        default="us-east-1",
        validation_alias="AWS_REGION",
        description="AWS region for services",
    )
    profile: Optional[str] = Field(
        default=None,
        validation_alias="AWS_PROFILE",
        description="AWS profile to use for authentication",
    )


class MetadataConfig(BaseSettings):
    """Metadata validation configuration."""

    model_config = ConfigDict(extra="allow")

    max_file_size_mb: int = Field(
        default=50, validation_alias="API_MAX_FILE_SIZE_MB", description="Maximum CSV file size in megabytes"
    )

    allowed_file_types: List[str] = Field(
        default=["text/csv", "application/csv"], description="Allowed MIME types for uploaded files"
    )

    validation_timeout_seconds: int = Field(
        default=300,
        validation_alias="API_VALIDATION_TIMEOUT_SECONDS",
        description="Maximum time allowed for validation processing",
    )

    enable_auth: bool = Field(
        default=False, validation_alias="API_ENABLE_AUTH", description="Enable or disable API authentication"
    )

    # MCP server settings
    mcp_enabled: bool = Field(
        default=True, validation_alias="MCP_ENABLED", description="Enable or disable MCP server integration"
    )

    mcp_mount_path: str = Field(
        default="/mcp", validation_alias="MCP_MOUNT_PATH", description="Mount path for MCP server endpoint"
    )


class ApiConfig(BaseSettings):
    """API configuration."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        validate_assignment=True,
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        validation_alias="LOG_LEVEL",
        description="Logging level for the application",
    )
    env_file: Path = Field(
        default=Path(".env"),
        validation_alias="ENV_FILE",
        description="Path to the .env file containing environment variables",
    )
    aws: AwsConfig = Field(
        default_factory=AwsConfig,
        description="AWS configuration settings",
    )
    metadata: MetadataConfig = Field(
        default_factory=MetadataConfig,
        description="Metadata validation configuration",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        """Convert log level to uppercase."""
        return v.upper()

    def model_post_init(self, context: Any) -> None:
        """Post-initialization for metadata API."""
        return super().model_post_init(context)


def load_api_configuration(config_path: Optional[Path] = None) -> Tuple[ApiConfig, ProcessorConfig]:
    """
    Load API and processor configuration from YAML file with environment overrides.

    Args:
        config_path: Optional path to configuration file. If None, uses default location.

    Returns:
        Tuple of (ApiConfig, ProcessorConfig) instances

    Raises:
        ValueError: If configuration validation fails
    """
    # Try multiple config path locations
    if config_path is None:
        possible_paths = [
            # Environment variable override
            Path(os.getenv("CONFIG_PATH", "")),
            # Docker container location
            Path("/app/config.yaml"),
            # API project config
            Path(__file__).parent.parent.parent / "config.yaml",
            # Current working directory
            Path("config.yaml"),
        ]

        config_path = None
        for path in possible_paths:
            logger.info(f"Checking Config Path: {path}")
            if path.exists() and path.is_file():
                config_path = path
                break

        if config_path is None:
            logger.warning(
                f"Configuration file not found in any of these locations: {[str(p) for p in possible_paths]}"
            )
            config_path = possible_paths[1]  # Use Docker path for error reporting
    # Load base configuration from YAML
    config_data = {}
    if config_path and config_path.exists():
        logger.info(f"Loading configuration from: {config_path}")
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {config_path}: {e}")
    else:
        logger.warning(f"Configuration file not found: {config_path}, using defaults")

    # Extract API configuration
    api_config_data = config_data.get("api", {})

    # Map API config to nested structure expected by ApiConfig
    metadata_config_data = {}
    api_env_mappings = {
        "API_MAX_FILE_SIZE_MB": "max_file_size_mb",
        "API_VALIDATION_TIMEOUT_SECONDS": "validation_timeout_seconds",
        "API_ENABLE_AUTH": "enable_auth",
        "MCP_ENABLED": "mcp_enabled",
        "MCP_MOUNT_PATH": "mcp_mount_path",
    }

    # Extract metadata-specific config from api section
    for field in [
        "max_file_size_mb",
        "allowed_file_types",
        "validation_timeout_seconds",
        "enable_auth",
        "mcp_enabled",
        "mcp_mount_path",
    ]:
        if field in api_config_data:
            metadata_config_data[field] = api_config_data[field]

    # Apply API environment variable overrides
    for env_var, config_key in api_env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            metadata_config_data[config_key] = value

    # Create API config with metadata section
    try:
        api_config_dict = {}
        if metadata_config_data:
            api_config_dict["metadata"] = metadata_config_data
        api_config = ApiConfig(**api_config_dict)
    except Exception as e:
        raise ValueError(f"API configuration validation failed: {e}")

    # Use processor's configuration loading system
    processor_config_data = config_data.get("processor", {})
    processor_overrides = {}

    if os.getenv("PROCESSOR_SESSION_S3_BUCKET"):
        processor_overrides["session_saver_type"] = "s3"
        processor_overrides["session_s3_bucket"] = os.getenv("PROCESSOR_SESSION_S3_BUCKET")
        processor_overrides["session_s3_prefix"] = "sessions/"

    if os.getenv("PROCESSOR_RESULTS_S3_BUCKET"):
        processor_overrides["result_saver_type"] = "s3"
        processor_overrides["results_s3_bucket"] = os.getenv("PROCESSOR_RESULTS_S3_BUCKET")
        processor_overrides["results_s3_prefix"] = "validation-results/"

    if os.getenv("PROCESSOR_JOB_STATUS_TABLE_NAME"):
        processor_overrides["job_status_saver_type"] = "dynamodb"
        processor_overrides["job_status_table_name"] = os.getenv("PROCESSOR_JOB_STATUS_TABLE_NAME")

    if os.getenv("PROCESSOR_ENABLE_MEMORY_CACHE") and not os.getenv("PROCESSOR_ENABLE_REDIS_CACHE"):
        processor_overrides["enable_memory_cache"] = os.getenv("PROCESSOR_ENABLE_MEMORY_CACHE")
        processor_overrides["enable_redis_cache"] = False

    if os.getenv("PROCESSOR_SCHEMA_DIRECTORY"):
        schema_dir_override = os.getenv("PROCESSOR_SCHEMA_DIRECTORY")
        logger.info(f"[CONFIG] Found PROCESSOR_SCHEMA_DIRECTORY env var: {schema_dir_override}")
        processor_overrides["schema_directory"] = schema_dir_override
    else:
        logger.info("[CONFIG] No PROCESSOR_SCHEMA_DIRECTORY env var found")

    if os.getenv("PROCESSOR_LOCAL_DEVELOPMENT_MODE"):
        processor_overrides["local_development_mode"] = os.getenv("PROCESSOR_LOCAL_DEVELOPMENT_MODE")

    processor_config_data = deep_merge_dicts(processor_config_data, processor_overrides)

    # Use the processor's configuration loading system
    try:
        processor_config = ProcessorConfig(**processor_config_data)
        # Force debug output of final schema directory value
        logger.info(f"[CONFIG] Final processor config schema_directory: {processor_config.schema_directory}")
    except Exception as e:
        logger.warning(f"Failed to load processor config from file: {e}")

    logger.info("Successfully loaded API and processor configurations")
    logger.debug(f"API config: {api_config.model_dump()}")
    logger.debug(f"Processor config: {processor_config.model_dump()}")

    return api_config, processor_config


# Create default configuration instances
api_config = ApiConfig()

# Load full configuration when imported
try:
    api_config, processor_config = load_api_configuration()
except Exception as e:
    logger.warning(f"Failed to load configuration from file: {e}")
    raise

if __name__ == "__main__":
    logger.info("API Config:")
    logger.info(api_config.model_dump())
    logger.info("\nProcessor Config:")
    logger.info(processor_config.model_dump())
