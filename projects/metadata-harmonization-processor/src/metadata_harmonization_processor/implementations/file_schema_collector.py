# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""File-based implementation of SchemaCollector interface."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from ..interfaces.schema_collector import SchemaCollector, SchemaInfo


class FileBasedSchemaCollector(SchemaCollector):
    """File-based implementation using catalog.json and schema directory."""

    def __init__(self, schema_directory: str):
        """Initialize with path to schema directory containing catalog.json.

        Args:
            schema_directory: Path to directory containing catalog.json and schema files

        Raises:
            FileNotFoundError: If schema directory or catalog.json doesn't exist
        """
        self.schema_directory = Path(schema_directory)
        self.catalog_path = self.schema_directory / "catalog.json"

        # Force debug output to see what paths are being used
        logger.info(f"[SCHEMA COLLECTOR INIT] schema_directory: {schema_directory}")
        logger.info(f"[SCHEMA COLLECTOR INIT] self.schema_directory: {self.schema_directory}")
        logger.info(f"[SCHEMA COLLECTOR INIT] self.catalog_path: {self.catalog_path}")
        logger.info(f"[SCHEMA COLLECTOR INIT] catalog_path.exists(): {self.catalog_path.exists()}")

        # Also check if the directory exists
        logger.info(f"[SCHEMA COLLECTOR INIT] schema_directory.exists(): {self.schema_directory.exists()}")

        # List contents of the directory if it exists
        if self.schema_directory.exists():
            try:
                contents = list(self.schema_directory.iterdir())
                logger.info(f"[SCHEMA COLLECTOR INIT] Directory contents: {[str(p) for p in contents]}")
            except Exception as e:
                logger.info(f"[SCHEMA COLLECTOR INIT] Error listing directory: {e}")

        logger.info(
            f"FileBasedSchemaCollector initialized with schema_directory={self.schema_directory}, catalog_path={self.catalog_path}"
        )

        # Validate directory and catalog exist
        if not self.schema_directory.exists():
            raise FileNotFoundError(
                f"Schema directory not found: {self.schema_directory} | ({self.schema_directory.absolute()})"
            )

        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog file not found: {self.catalog_path}")

        # Cache for loaded data
        self._catalog_cache: list[dict[str, Any]] | None = None
        self._schema_cache: dict[str, dict[str, Any]] = {}

        logger.info(f"Initialized FileBasedSchemaCollector with directory: {self.schema_directory}")

    async def get_available_schemas(self) -> list[SchemaInfo]:
        """Load catalog.json and return available schema combinations.

        Returns:
            List of SchemaInfo objects representing all available core/program combinations

        Raises:
            FileNotFoundError: If catalog.json is missing
            json.JSONDecodeError: If catalog.json is invalid JSON
            KeyError: If catalog.json has unexpected structure
        """
        try:
            catalog = await self._load_catalog()
            schemas = []

            for core_entry in catalog:
                # Validate required core fields
                if not all(key in core_entry for key in ["core_uuid", "core_name", "core_path", "program"]):
                    logger.warning(f"Skipping invalid core entry missing required fields: {core_entry}")
                    continue

                for program_entry in core_entry["program"]:
                    # Validate required program fields
                    if not all(key in program_entry for key in ["program_uuid", "program_name", "program_path"]):
                        logger.warning(f"Skipping invalid program entry missing required fields: {program_entry}")
                        continue

                    schemas.append(
                        SchemaInfo(
                            core_uuid=core_entry["core_uuid"],
                            core_name=core_entry["core_name"],
                            core_path=core_entry["core_path"],
                            program_uuid=program_entry["program_uuid"],
                            program_name=program_entry["program_name"],
                            program_path=program_entry["program_path"],
                        )
                    )

            logger.info(f"Found {len(schemas)} available schema combinations")
            return schemas

        except FileNotFoundError:
            logger.error(f"Catalog file not found: {self.catalog_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in catalog file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading available schemas: {e}")
            raise

    async def get_schema(self, program_id: str, core_id: str) -> dict[str, Any]:
        """Load and combine core and program schemas.

        Args:
            program_id: UUID of the program schema
            core_id: UUID of the core schema

        Returns:
            Combined schema definition with program schema merged into core schema

        Raises:
            ValueError: If schema IDs are not found in catalog
            FileNotFoundError: If schema files are missing
            json.JSONDecodeError: If schema files contain invalid JSON
        """
        logger.info(f"Starting schema lookup for program_id={program_id}, core_id={core_id}")

        try:
            # Find schema paths from catalog
            logger.debug(f"Looking up schema paths in catalog for program_id={program_id}, core_id={core_id}")
            core_path, program_path = await self._find_schema_paths(program_id, core_id)
            logger.info(f"Found schema paths: core={core_path}, program={program_path}")

            # Load both schemas
            logger.debug(f"Loading core schema from {core_path}")
            core_schema = await self._load_schema_file(core_path)
            logger.debug(f"Successfully loaded core schema with {len(core_schema.get('properties', {}))} properties")

            logger.debug(f"Loading program schema from {program_path}")
            program_schema = await self._load_schema_file(program_path)
            logger.debug(
                f"Successfully loaded program schema with {len(program_schema.get('properties', {}))} properties"
            )

            # Combine schemas - program schema properties override/extend core schema
            combined_schema = core_schema.copy()

            # Merge properties
            if "properties" in program_schema:
                if "properties" not in combined_schema:
                    combined_schema["properties"] = {}
                original_property_count = len(combined_schema["properties"])
                combined_schema["properties"].update(program_schema["properties"])
                logger.debug(f"Merged properties: {original_property_count} -> {len(combined_schema['properties'])}")

            # Merge required fields
            if "required" in program_schema:
                if "required" not in combined_schema:
                    combined_schema["required"] = []
                original_required_count = len(combined_schema["required"])
                # Combine and deduplicate required fields
                combined_required = list(set(combined_schema["required"] + program_schema["required"]))
                combined_schema["required"] = combined_required
                logger.debug(f"Merged required fields: {original_required_count} -> {len(combined_required)}")

            # Update title and description to reflect combination
            combined_schema[
                "title"
            ] = f"Combined {core_schema.get('title', 'Core')} and {program_schema.get('title', 'Program')} Schema"
            combined_schema["description"] = f"Combined schema for core_id={core_id} and program_id={program_id}"

            logger.info(
                f"Successfully combined schemas for core_id={core_id}, program_id={program_id} with {len(combined_schema.get('properties', {}))} total properties"
            )
            return combined_schema

        except ValueError as e:
            logger.error(
                f"Schema combination failed - invalid schema IDs: core_id={core_id}, program_id={program_id}. Error: {e}"
            )
            raise
        except FileNotFoundError as e:
            logger.error(
                f"Schema combination failed - file not found: core_id={core_id}, program_id={program_id}. Error: {e}"
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(
                f"Schema combination failed - invalid JSON in schema file: core_id={core_id}, program_id={program_id}. Error: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Schema combination failed with unexpected error: core_id={core_id}, program_id={program_id}. Error: {e}"
            )
            logger.exception("Full exception details:")
            raise

    async def get_schema_columns(self, program_id: str, core_id: str) -> list[str]:
        """Get list of expected columns for schema.

        Args:
            program_id: UUID of the program schema
            core_id: UUID of the core schema

        Returns:
            List of column names from the combined schema properties

        Raises:
            ValueError: If schema IDs are not found
            Exception: If schema cannot be loaded
        """
        try:
            combined_schema = await self.get_schema(program_id, core_id)

            # Extract column names from properties
            columns = []
            if "properties" in combined_schema:
                columns = list(combined_schema["properties"].keys())

            logger.info(f"Found {len(columns)} columns for core_id={core_id}, program_id={program_id}")
            return columns

        except Exception as e:
            logger.error(f"Error getting schema columns for core_id={core_id}, program_id={program_id}: {e}")
            raise

    async def get_validation_rules(self, program_id: str, core_id: str) -> dict[str, Any]:
        """Get validation rules for schema fields.

        Args:
            program_id: UUID of the program schema
            core_id: UUID of the core schema

        Returns:
            Dictionary mapping field names to their validation rules

        Raises:
            ValueError: If schema IDs are not found
            Exception: If schema cannot be loaded
        """
        try:
            combined_schema = await self.get_schema(program_id, core_id)

            validation_rules = {}

            if "properties" in combined_schema:
                for field_name, field_schema in combined_schema["properties"].items():
                    rules = {}

                    # Extract validation rules from JSON schema
                    if "type" in field_schema:
                        rules["type"] = field_schema["type"]

                    if "enum" in field_schema:
                        rules["options"] = field_schema["enum"]

                    if "pattern" in field_schema:
                        rules["pattern"] = field_schema["pattern"]

                    if "minLength" in field_schema:
                        rules["min_length"] = field_schema["minLength"]

                    if "maxLength" in field_schema:
                        rules["max_length"] = field_schema["maxLength"]

                    # Check if field is required
                    required_fields = combined_schema.get("required", [])
                    rules["required"] = field_name in required_fields

                    # Include custom validation attributes
                    if "amdValidation" in field_schema:
                        rules["amd_validation"] = field_schema["amdValidation"]

                    if "amdValidationOptions" in field_schema:
                        rules["amd_validation_options"] = field_schema["amdValidationOptions"]

                    # Include error messages
                    if "errorMessage" in field_schema:
                        rules["error_message"] = field_schema["errorMessage"]

                    validation_rules[field_name] = rules

            logger.info(f"Extracted validation rules for {len(validation_rules)} fields")
            return validation_rules

        except Exception as e:
            logger.error(f"Error getting validation rules for core_id={core_id}, program_id={program_id}: {e}")
            raise

    async def _load_catalog(self) -> list[dict[str, Any]]:
        """Load and cache catalog.json.

        Returns:
            Parsed catalog data as list of dictionaries

        Raises:
            FileNotFoundError: If catalog.json doesn't exist
            json.JSONDecodeError: If catalog.json is invalid JSON
        """
        if self._catalog_cache is None:
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    self._catalog_cache = json.load(f)
                logger.debug(f"Loaded catalog with {len(self._catalog_cache)} entries")
            except FileNotFoundError:
                logger.error(f"Catalog file not found: {self.catalog_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in catalog file: {e}")
                raise

        return self._catalog_cache

    async def _load_schema_file(self, schema_path: str) -> dict[str, Any]:
        """Load and cache individual schema file.

        Args:
            schema_path: Relative path to schema file from schema directory

        Returns:
            Parsed schema data as dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is invalid JSON
        """
        if schema_path not in self._schema_cache:
            full_path = self.schema_directory / schema_path

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    self._schema_cache[schema_path] = json.load(f)
                logger.debug(f"Loaded schema file: {schema_path}")
            except FileNotFoundError:
                logger.error(f"Schema file not found: {full_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in schema file {full_path}: {e}")
                raise

        return self._schema_cache[schema_path]

    async def _find_schema_paths(self, program_id: str, core_id: str) -> tuple[str, str]:
        """Find schema file paths for given IDs.

        Args:
            program_id: UUID of the program schema
            core_id: UUID of the core schema

        Returns:
            Tuple of (core_path, program_path)

        Raises:
            ValueError: If schema IDs are not found in catalog
        """
        logger.debug(f"Searching catalog for schema paths: core_id={core_id}, program_id={program_id}")
        catalog = await self._load_catalog()
        logger.debug(f"Loaded catalog with {len(catalog)} core entries")

        for core_entry in catalog:
            logger.debug(f"Checking core entry: {core_entry.get('core_uuid')} vs {core_id}")
            if core_entry.get("core_uuid") == core_id:
                core_path = core_entry.get("core_path")
                logger.debug(f"Found matching core entry with path: {core_path}")

                programs = core_entry.get("program", [])
                logger.debug(f"Checking {len(programs)} program entries")

                for program_entry in programs:
                    logger.debug(f"Checking program entry: {program_entry.get('program_uuid')} vs {program_id}")
                    if program_entry.get("program_uuid") == program_id:
                        program_path = program_entry.get("program_path")
                        logger.info(f"Found matching schema paths: core={core_path}, program={program_path}")
                        return core_path, program_path

                # Log available program IDs for debugging
                available_program_ids = [p.get("program_uuid") for p in programs]
                logger.warning(
                    f"Program ID {program_id} not found. Available program IDs for core {core_id}: {available_program_ids}"
                )

        # Log available core IDs for debugging
        available_core_ids = [c.get("core_uuid") for c in catalog]
        logger.error(
            f"Schema combination not found: core_id={core_id}, program_id={program_id}. Available core IDs: {available_core_ids}"
        )
        raise ValueError(f"Schema combination not found: core_id={core_id}, program_id={program_id}")
