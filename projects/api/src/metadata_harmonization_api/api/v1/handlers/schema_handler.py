# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Handler for schema management business logic."""

import logging
from typing import List

from fastapi import HTTPException, Request

from metadata_harmonization_api.api.v1.models.metadata import (
    SchemaInfo,
)
from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector


logger = logging.getLogger(__name__)


class SchemaHandler:
    """Handler for schema management business logic."""

    def __init__(self, schema_collector: SchemaCollector):
        """
        Initialize the schema handler.

        Args:
            schema_collector: Schema collector for retrieving available schemas
        """
        self.schema_collector = schema_collector

    async def get_available_schemas(self, request: Request) -> List[SchemaInfo]:
        """
        Get all available schemas for UI selection.

        Args:
            request: FastAPI request object

        Returns:
            List of SchemaInfo objects with core and program schema information

        Raises:
            HTTPException: If schema retrieval fails
        """
        # Get request context for logging
        request_id = getattr(request.state, "request_id", "unknown")
        user_id = getattr(request.state, "user_id", "unknown")

        logger.info(
            f"Retrieving available schemas for user {user_id}", extra={"request_id": request_id, "user_id": user_id}
        )

        try:
            # Get all schemas from schema collector
            logger.debug("Calling schema_collector.get_available_schemas()")
            collector_schemas = await self.schema_collector.get_available_schemas()
            logger.info(f"Schema collector returned {len(collector_schemas)} schema combinations")

            # Group by core schema to match API format
            core_schemas = {}
            total_program_schemas = 0

            for i, schema_info in enumerate(collector_schemas):
                logger.debug(
                    f"Processing schema {i+1}/{len(collector_schemas)}: core={schema_info.core_uuid}, program={schema_info.program_uuid}"
                )

                core_id = schema_info.core_uuid
                if core_id not in core_schemas:
                    core_schemas[core_id] = {
                        "core_schema_id": core_id,
                        "name": schema_info.core_name,
                        "core_schema_path": schema_info.core_path,
                        "core_schema_s3_bucket": "metadata-schemas",  # Default bucket
                        "program_schemas": [],
                    }
                    logger.debug(f"Created new core schema group: {schema_info.core_name}")

                program_schema = {
                    "program_name": schema_info.program_name,
                    "s3_location": schema_info.program_path,
                    "s3_bucket": "metadata-schemas",  # Default bucket
                    "program_schema_id": schema_info.program_uuid,
                }

                core_schemas[core_id]["program_schemas"].append(program_schema)
                total_program_schemas += 1
                logger.debug(f"Added program schema: {schema_info.program_name}")

            # Convert to API response format
            logger.debug("Converting to API response format")
            schema_infos = [SchemaInfo(**schema_data) for schema_data in core_schemas.values()]

            logger.info(
                f"Successfully retrieved {len(schema_infos)} core schemas with {total_program_schemas} total program schemas",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "core_schema_count": len(schema_infos),
                    "program_schema_count": total_program_schemas,
                },
            )

            return schema_infos

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving available schemas for user {user_id}: {e}",
                extra={"request_id": request_id, "user_id": user_id, "error_type": type(e).__name__},
            )
            logger.exception("Full exception details:")
            raise HTTPException(status_code=500, detail="Internal server error while retrieving available schemas")
