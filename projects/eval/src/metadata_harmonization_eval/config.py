# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Configuration management for the evaluation package.

This module provides utilities for loading, validating, and managing
evaluation configuration from YAML files or defaults.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger

from .models import EvaluationConfig


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


def load_config(config_path: Optional[Path] = None) -> EvaluationConfig:
    """
    Load evaluation configuration from file or use defaults.

    This is the main entry point for loading configuration. It handles:
    - Loading from YAML file if path provided
    - Using defaults if no path provided
    - Validating all required fields
    - Applying defaults for optional fields
    - Graceful error handling with helpful messages

    Args:
        config_path: Optional path to YAML configuration file.
                    If None, uses default configuration.

    Returns:
        EvaluationConfig instance with validated settings

    Raises:
        ConfigurationError: If configuration is invalid or cannot be loaded

    Examples:
        >>> # Load from file
        >>> config = load_config(Path("config.yaml"))

        >>> # Use defaults
        >>> config = load_config()
    """
    if config_path is None:
        logger.info("No configuration file provided, using defaults")
        return EvaluationConfig.from_defaults()

    try:
        config = EvaluationConfig.from_yaml(config_path)
        _validate_config(config)
        logger.info(f"Configuration loaded successfully from {config_path}")
        return config
    except FileNotFoundError as e:
        raise ConfigurationError(f"Configuration file not found: {config_path}") from e
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML syntax in {config_path}: {e}") from e
    except ValueError as e:
        raise ConfigurationError(f"Invalid configuration values: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Unexpected error loading configuration: {e}") from e


def _validate_config(config: EvaluationConfig) -> None:
    """
    Validate configuration settings.

    Performs additional validation beyond Pydantic's built-in checks:
    - Verifies paths exist or can be created
    - Validates schema IDs are non-empty
    - Checks report formats are valid
    - Validates numeric ranges

    Args:
        config: Configuration to validate

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate processor config path exists
    if not config.processor_config_path.exists():
        raise ConfigurationError(f"Processor configuration file not found: {config.processor_config_path}")

    # Validate data directory exists
    if not config.data_directory.exists():
        raise ConfigurationError(f"Data directory not found: {config.data_directory}")

    # Validate schema IDs are not empty
    if not config.schema_program_id.strip():
        raise ConfigurationError("schema_program_id cannot be empty")

    if not config.schema_core_id.strip():
        raise ConfigurationError("schema_core_id cannot be empty")

    # Validate report formats
    valid_formats = {"json", "markdown"}
    for fmt in config.report_formats:
        if fmt not in valid_formats:
            raise ConfigurationError(f"Invalid report format '{fmt}'. Must be one of: {valid_formats}")

    # Validate confidence threshold
    if not 0.0 <= config.confidence_threshold <= 1.0:
        raise ConfigurationError(f"confidence_threshold must be between 0.0 and 1.0, got {config.confidence_threshold}")

    # Try to create output directory if it doesn't exist
    try:
        config.output_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ConfigurationError(f"Cannot create output directory {config.output_directory}: {e}") from e


def load_yaml_file(path: Path) -> Dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Dictionary of parsed YAML data

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r") as f:
        try:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {path}: {e}") from e


def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """
    Validate that required fields are present in configuration data.

    Args:
        data: Configuration dictionary
        required_fields: List of required field names

    Raises:
        ConfigurationError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ConfigurationError(f"Missing required configuration fields: {', '.join(missing_fields)}")


def apply_defaults(data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values for missing optional fields.

    Args:
        data: Configuration dictionary
        defaults: Dictionary of default values

    Returns:
        Configuration dictionary with defaults applied
    """
    result = data.copy()

    for key, default_value in defaults.items():
        if key not in result:
            result[key] = default_value
            logger.debug(f"Applied default value for '{key}': {default_value}")

    return result


def get_default_config_values() -> Dict[str, Any]:
    """
    Get dictionary of default configuration values.

    Returns:
        Dictionary with default values for optional fields
    """
    return {
        "output_directory": "evaluation_results",
        "report_formats": ["json", "markdown"],
        "include_visualizations": True,
        "confidence_threshold": 0.5,
        "verbose_logging": False,
    }


def create_example_config(output_path: Path) -> None:
    """
    Create an example configuration file.

    Args:
        output_path: Where to write the example config file

    Raises:
        IOError: If file cannot be written
    """
    example_config = {
        "processor_config_path": "../../config.yaml",
        "data_directory": "../../data/synthetic_dataset",
        "schema_program_id": "cyclospora_program",
        "schema_core_id": "cyclospora_core",
        "output_directory": "evaluation_results",
        "report_formats": ["json", "markdown"],
        "include_visualizations": True,
        "confidence_threshold": 0.5,
        "verbose_logging": False,
    }

    with open(output_path, "w") as f:
        yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Example configuration written to {output_path}")
