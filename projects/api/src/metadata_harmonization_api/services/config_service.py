# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Configuration service for metadata validation."""

from pathlib import Path
from typing import Dict, Any

from metadata_harmonization_api.config import api_config


class MetadataConfigService:
    """Service for managing metadata validation configuration."""

    def __init__(self):
        """Initialize the configuration service."""
        self.config = api_config.metadata
        self.storage_config = api_config.storage
        self.aws_config = api_config.aws

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.config.max_file_size_mb * 1024 * 1024

    @property
    def allowed_file_types(self) -> set[str]:
        """Get allowed MIME types for file uploads."""
        return set(self.config.allowed_file_types)

    @property
    def validation_timeout_seconds(self) -> int:
        """Get validation timeout in seconds."""
        return self.config.validation_timeout_seconds

    @property
    def schema_directory(self) -> Path:
        """Get schema directory path."""
        return self.config.schema_directory

    @property
    def results_s3_bucket(self) -> str:
        """Get S3 bucket for validation results."""
        return self.config.results_s3_bucket

    @property
    def schemas_s3_bucket(self) -> str:
        """Get S3 bucket for validation schemas."""
        return self.config.schemas_s3_bucket

    @property
    def schemas_table_name(self) -> str:
        """Get DynamoDB table name for metadata schemas."""
        return self.storage_config.metadata_schemas_table

    @property
    def upload_jobs_table_name(self) -> str:
        """Get DynamoDB table name for upload jobs."""
        return self.storage_config.metadata_upload_jobs_table

    @property
    def aws_region(self) -> str:
        """Get AWS region."""
        return self.aws_config.region

    def get_table_config(self) -> Dict[str, str]:
        """Get DynamoDB table configuration."""
        return {
            "schemas_table": self.schemas_table_name,
            "jobs_table": self.upload_jobs_table_name,
            "region": self.aws_region,
        }

    def get_s3_config(self) -> Dict[str, str]:
        """Get S3 configuration."""
        return {
            "results_bucket": self.results_s3_bucket,
            "schemas_bucket": self.schemas_s3_bucket,
            "region": self.aws_region,
        }

    def get_file_validation_config(self) -> Dict[str, Any]:
        """Get file validation configuration."""
        return {
            "max_size_bytes": self.max_file_size_bytes,
            "max_size_mb": self.config.max_file_size_mb,
            "allowed_types": list(self.allowed_file_types),
            "timeout_seconds": self.validation_timeout_seconds,
        }

    def validate_configuration(self) -> Dict[str, bool]:
        """Validate that all required configuration is present."""
        validation_results = {
            "has_schemas_table": bool(self.schemas_table_name),
            "has_jobs_table": bool(self.upload_jobs_table_name),
            "has_results_bucket": bool(self.results_s3_bucket),
            "has_schemas_bucket": bool(self.schemas_s3_bucket),
            "has_aws_region": bool(self.aws_region),
            "has_schema_directory": self.schema_directory.exists() if self.schema_directory else False,
            "valid_file_size": self.config.max_file_size_mb > 0,
            "valid_timeout": self.validation_timeout_seconds > 0,
        }

        return validation_results

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of all metadata configuration."""
        return {
            "file_validation": self.get_file_validation_config(),
            "storage": {"dynamodb": self.get_table_config(), "s3": self.get_s3_config()},
            "schema_directory": str(self.schema_directory),
            "validation_status": self.validate_configuration(),
        }


# Global instance
metadata_config_service = MetadataConfigService()
