# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Result storage interface for metadata harmonization processor."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.combined_results import CombinedResults
from ..models.job import JobResults


class ResultSaver(ABC):
    """Interface for storing and retrieving CombinedResults using single results.json file storage.

    This interface provides a simplified storage approach where both validation results
    and schema alignment results are stored together in a single results.json file,
    eliminating the need for separate artifact files.
    """

    @abstractmethod
    async def save_results(
        self,
        job_id: str,
        version: int,
        combined_results: CombinedResults,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobResults:
        """Save CombinedResults to single results.json file.

        This method stores the entire CombinedResults instance as a single JSON file
        using combined_results.to_dict() for serialization. No separate artifact files
        (column_mappings.json, transformation_summary.json, etc.) are created.

        Args:
            job_id: Unique identifier for the processing job
            version: Version number for this result set
            combined_results: CombinedResults instance containing both validation and schema alignment data
            metadata: Optional metadata about the processing

        Returns:
            JobResults with storage location information

        Raises:
            Exception: If results cannot be saved
        """
        pass

    @abstractmethod
    async def get_results(self, job_results: JobResults) -> Optional[CombinedResults]:
        """Retrieve CombinedResults from single results.json file.

        This method loads the results.json file and reconstructs the CombinedResults
        instance using CombinedResults.from_dict() for deserialization.

        Args:
            job_results: JobResults with storage location information

        Returns:
            CombinedResults instance or None if not found

        Raises:
            Exception: If results cannot be retrieved
        """
        pass

    @abstractmethod
    async def list_results(self, job_id: str) -> List[JobResults]:
        """List all saved results for a job across versions.

        Args:
            job_id: Unique identifier for the processing job

        Returns:
            List of JobResults for all versions of this job

        Raises:
            Exception: If results cannot be listed
        """
        pass
