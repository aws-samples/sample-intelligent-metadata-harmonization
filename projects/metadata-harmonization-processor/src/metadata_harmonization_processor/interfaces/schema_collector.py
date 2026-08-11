# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Schema collection interface for metadata harmonization processor."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class SchemaInfo(BaseModel):
    """Schema information for API responses."""

    core_uuid: str = Field(..., description="Unique identifier for the core schema")
    core_name: str = Field(..., description="Human-readable name of the core schema")
    core_path: str = Field(..., description="File path to the core schema")
    program_uuid: str = Field(..., description="Unique identifier for the program schema")
    program_name: str = Field(..., description="Human-readable name of the program schema")
    program_path: str = Field(..., description="File path to the program schema")


class SchemaCollector(ABC):
    """Interface for collecting schema information."""

    @abstractmethod
    async def get_available_schemas(self) -> List[SchemaInfo]:
        """Get list of available schemas for API get_available_schemas endpoint.

        Returns:
            List of SchemaInfo objects representing available schema combinations

        Raises:
            Exception: If schemas cannot be retrieved
        """
        pass

    @abstractmethod
    async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Retrieve combined schema definition by program and core IDs.

        Args:
            program_id: Identifier for the program schema
            core_id: Identifier for the core schema

        Returns:
            Combined schema definition as a dictionary

        Raises:
            Exception: If schema cannot be retrieved or combined
        """
        pass

    @abstractmethod
    async def get_schema_columns(self, program_id: str, core_id: str) -> List[str]:
        """Get list of expected columns for schema.

        Args:
            program_id: Identifier for the program schema
            core_id: Identifier for the core schema

        Returns:
            List of column names expected by the schema

        Raises:
            Exception: If schema columns cannot be determined
        """
        pass

    @abstractmethod
    async def get_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Get validation rules for schema fields.

        Args:
            program_id: Identifier for the program schema
            core_id: Identifier for the core schema

        Returns:
            Dictionary mapping field names to their validation rules

        Raises:
            Exception: If validation rules cannot be retrieved
        """
        pass
