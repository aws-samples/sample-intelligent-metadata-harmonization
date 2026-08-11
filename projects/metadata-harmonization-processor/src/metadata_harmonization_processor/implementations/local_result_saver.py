# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Local file implementation of ResultSaver for development environments.

This module provides local file-based storage for combined ValidationResults and
SchemaAlignmentResults with proper error handling, directory management, and
support for both absolute and relative paths.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..interfaces.result_saver import ResultSaver
from ..models.combined_results import CombinedResults
from ..models.job import JobResults


class LocalResultSaver(ResultSaver):
    """Local file implementation of ResultSaver for development environments.

    Stores CombinedResults as a single results.json file in a local directory.
    The entire CombinedResults instance is serialized to JSON and stored as a single
    file, eliminating the need for separate artifact files. Supports both absolute
    and relative paths and provides proper error handling for file system operations.
    """

    def __init__(self, storage_dir: str = "./data/validation-results"):
        """Initialize LocalResultSaver with local storage configuration.

        Args:
            storage_dir: Local directory for storing result files.
                        Supports both absolute and relative paths.

        Raises:
            ValueError: If storage_dir is empty
            OSError: If directory cannot be created
        """
        if not storage_dir:
            raise ValueError("storage_dir cannot be empty")

        self.storage_dir = Path(storage_dir).resolve()

        try:
            # Create directory if it doesn't exist
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized LocalResultSaver with storage directory: {self.storage_dir}")
        except OSError as e:
            logger.error(f"Failed to create storage directory {self.storage_dir}: {e}")
            raise

    async def save_results(
        self,
        job_id: str,
        version: int,
        combined_results: CombinedResults,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobResults:
        """Save CombinedResults to single results.json file in local directory.

        The entire CombinedResults instance is serialized using combined_results.to_dict()
        and stored as a single JSON file at:
        - {job_id}/v{version}/results.json

        Args:
            job_id: Unique identifier for the processing job
            version: Version number for this result set
            combined_results: CombinedResults instance containing both validation and schema alignment data
            metadata: Optional metadata about the processing

        Returns:
            JobResults with local storage location information

        Raises:
            ValueError: If job_id is empty or version is invalid
            OSError: If file operations fail
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")
        if version < 1:
            raise ValueError("version must be >= 1")

        # Create directory for this job/version
        job_dir = self.storage_dir / job_id / f"v{version}"
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Save combined results to single file
            results_file = job_dir / "results.json"

            # Prepare data for storage using single file approach
            storage_data = {
                "job_id": job_id,
                "version": version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "combined_results": combined_results.to_dict(),
                "metadata": metadata or {},
            }

            # Write JSON data to file
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Successfully saved combined results for job {job_id} version {version}")

            # Return JobResults pointing to the results.json file
            return JobResults(
                storage_type="local",
                location=str(results_file.relative_to(self.storage_dir)),
            )

        except Exception as e:
            logger.error(f"Failed to save combined results for job {job_id}: {e}")
            raise

    async def get_results(self, job_results: JobResults) -> Optional[CombinedResults]:
        """Retrieve CombinedResults from single results.json file in local directory.

        Args:
            job_results: JobResults with local storage location information

        Returns:
            CombinedResults instance or None if not found

        Raises:
            ValueError: If job_results is not for local storage
            OSError: If file operations fail
            json.JSONDecodeError: If file contains invalid JSON
        """
        if job_results.storage_type != "local":
            raise ValueError(f"Expected local storage type, got: {job_results.storage_type}")

        logger.info("LocalResultSaver attempting to load results")
        logger.info(f"  Storage directory: {self.storage_dir}")
        logger.info(f"  Location from JobResults: {job_results.location}")

        try:
            # Get results from single results.json file
            results_path = Path(job_results.location)
            logger.debug(f"  Initial path object: {results_path}")

            # Handle both directory and file paths for backward compatibility
            if not results_path.name.endswith("results.json"):
                logger.debug("  Path doesn't end with results.json, appending it")
                results_path = results_path / "results.json"
            else:
                logger.debug("  Path already ends with results.json, using as-is")

            logger.debug(f"  Path after adjustment: {results_path}")

            file_path = self.storage_dir / results_path
            logger.info(f"  Resolved file path: {file_path}")

            try:
                # Check if file exists
                file_exists = file_path.exists()
                logger.info(f"  File exists: {file_exists}")

                if not file_exists:
                    logger.warning("  Results file not found at expected location")
                    logger.warning(f"  Expected path: {file_path}")
                    logger.warning("  Check that storage_dir is correct and job completed successfully")
                    return None

                logger.info("  Successfully located results file, reading content...")

                # Read and parse JSON data
                with open(file_path, "r", encoding="utf-8") as f:
                    storage_data = json.load(f)

                logger.info("  Successfully loaded and parsed results JSON")

                # Extract CombinedResults from storage format
                combined_results_data = storage_data.get("combined_results")

                # Reconstruct CombinedResults using from_dict method
                return CombinedResults.from_dict(combined_results_data)

            except OSError as e:
                logger.error(f"Failed to read combined results from local file {file_path}: {e}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from local file {file_path}: {e}")
                raise

        except Exception as e:
            logger.error(f"Unexpected error retrieving combined results from local files: {e}")
            raise

    async def list_results(self, job_id: str) -> List[JobResults]:
        """List all saved results for a job by scanning local directory structure.

        Args:
            job_id: Unique identifier for the processing job

        Returns:
            List of JobResults for all versions of this job, sorted by version

        Raises:
            ValueError: If job_id is empty
            OSError: If directory operations fail
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        job_dir = self.storage_dir / job_id
        results = []

        try:
            # Check if job directory exists
            if not job_dir.exists():
                logger.info(f"No results directory found for job {job_id}")
                return results

            # Scan for version directories
            for version_dir in job_dir.iterdir():
                if version_dir.is_dir() and version_dir.name.startswith("v"):
                    results_file = version_dir / "results.json"

                    if results_file.exists():
                        try:
                            # Extract version number from directory name (validates the pattern)
                            version_str = version_dir.name[1:]  # Remove 'v' prefix
                            int(version_str)

                            # Create relative path to directory from storage_dir
                            relative_path = version_dir.relative_to(self.storage_dir)

                            # Return full path to results.json file for single file storage
                            results_file_path = relative_path / "results.json"
                            results.append(
                                JobResults(
                                    storage_type="local",
                                    location=str(results_file_path),
                                )
                            )
                        except (ValueError, OSError) as e:
                            # Skip directories that don't match expected pattern
                            logger.debug(f"Skipping directory with unexpected pattern: {version_dir.name} - {e}")
                            continue

            # Sort by version number
            def extract_version(job_result: JobResults) -> int:
                try:
                    # Extract version from location: {job_id}/v{version}/results.json
                    path_parts = Path(job_result.location.rstrip("/")).parts
                    if len(path_parts) >= 2:
                        version_part = path_parts[-2]  # v{version} directory, one above the file
                        if version_part.startswith("v"):
                            return int(version_part[1:])
                except (ValueError, IndexError):
                    pass
                return 0

            results.sort(key=extract_version)

            logger.info(f"Found {len(results)} result versions for job {job_id}")
            return results

        except OSError as e:
            logger.error(f"Failed to list results from local directory {job_dir}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing results from local directory: {e}")
            raise
