# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for change tracking integration in API responses."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.api.v1.models.metadata import ValidationStatusResponse
from metadata_harmonization_processor.models.job import MetadataUploadJob
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.change_tracking import ChangeTrackingResults, ChangeObject, ChangesSummary
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationResultsSummary,
    ValidationErrorDetail,
    ValidationErrorType,
)


class TestChangeTrackingAPIIntegration:
    """Test cases for change tracking integration in API responses."""

    @pytest.fixture
    def mock_schema_collector(self):
        """Create a mock SchemaCollector."""
        mock = AsyncMock()
        mock.get_schema.return_value = {"test": "schema"}
        return mock

    @pytest.fixture
    def mock_job_status_saver(self):
        """Create a mock JobStatusSaver."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_processor_manager(self):
        """Create a mock ProcessorManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_processor(self):
        """Create a mock processor with data_saver."""
        mock = AsyncMock()
        mock.data_saver = AsyncMock()
        return mock

    @pytest.fixture
    def handler(self, mock_schema_collector, mock_job_status_saver, mock_processor_manager):
        """Create a MetadataValidationHandler instance."""
        return MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

    @pytest.fixture
    def sample_job(self):
        """Create a sample MetadataUploadJob."""
        from metadata_harmonization_processor.models.job import JobResults

        job_id = str(uuid4())
        return MetadataUploadJob(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="completed",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_version=2,
            results={"2": JobResults(storage_type="local", location="/path/to/results.json")},
        )

    @pytest.fixture
    def sample_processor_change_tracking(self):
        """Create sample processor change tracking results."""
        changes = [
            ChangeObject(
                change_id="chg_001",
                change_type="rename",
                source_type="user",
                component="validation",
                column="A1",
                row=1,
                old_value="old_name",
                new_value="new_name",
                timestamp="2025-01-01T12:00:00Z",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_id="chg_002",
                change_type="add",
                source_type="system",
                component="schema_alignment",
                column="status",
                new_value="active",
                timestamp="2025-01-01T12:00:00Z",
                source_version=1,
                target_version=2,
                confidence_score=0.8,
            ),
        ]

        summary = ChangesSummary(total_changes=2, adds=1, removes=0, renames=1, system_changes=1, user_changes=1)

        return ChangeTrackingResults(
            changes=changes,
            summary=summary,
            comparison_metadata={"detection_timestamp": "2025-01-01T12:00:00Z", "compared_versions": [1, 2]},
        )

    @pytest.fixture
    def sample_processor_combined_results(self, sample_processor_change_tracking):
        """Create sample processor combined results with change tracking."""
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="participant_id",
                    current_value="",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    recommended_value="P001",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        return CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=None,
            change_tracking=sample_processor_change_tracking,
        )

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.state.user_id = "test_user_123"
        return request

    @pytest.mark.asyncio
    async def test_get_validation_status_with_change_tracking(
        self, handler, sample_job, sample_processor_combined_results, mock_processor, mock_request
    ):
        """Test get_validation_status includes change tracking data in response."""
        # Setup mocks
        handler.job_status_saver.get_job.return_value = sample_job
        handler.processor_manager.get_processor.return_value = mock_processor
        handler.processor_manager.cleanup_processor.return_value = None
        mock_processor.data_saver.get_results.return_value = sample_processor_combined_results

        # Call the method
        response = await handler.get_validation_status(metadata_id=UUID(sample_job.job_id), request=mock_request)

        # Verify response structure
        assert isinstance(response, ValidationStatusResponse)
        assert response.job_id == UUID(sample_job.job_id)
        assert response.status == "completed"
        assert response.latest_results is not None

        # Verify change tracking is included
        assert response.latest_results.change_tracking is not None
        change_tracking = response.latest_results.change_tracking

        # Verify change tracking structure
        assert isinstance(change_tracking, ChangeTrackingResults)
        assert len(change_tracking.changes) == 2
        assert change_tracking.summary.total_changes == 2
        assert change_tracking.summary.adds == 1
        assert change_tracking.summary.renames == 1
        assert change_tracking.summary.system_changes == 1
        assert change_tracking.summary.user_changes == 1

        # Verify individual changes
        changes = change_tracking.changes
        rename_change = next(c for c in changes if c.change_type == "rename")
        add_change = next(c for c in changes if c.change_type == "add")

        assert rename_change.change_id == "chg_001"
        assert rename_change.source_type == "user"
        assert rename_change.component == "validation"
        assert rename_change.old_value == "old_name"
        assert rename_change.new_value == "new_name"

        assert add_change.change_id == "chg_002"
        assert add_change.source_type == "system"
        assert add_change.component == "schema_alignment"
        assert add_change.new_value == "active"
        assert add_change.confidence_score == 0.8

        # Verify comparison metadata
        assert change_tracking.comparison_metadata["detection_timestamp"] == "2025-01-01T12:00:00Z"
        assert change_tracking.comparison_metadata["compared_versions"] == [1, 2]

    @pytest.mark.asyncio
    async def test_get_validation_status_without_change_tracking(
        self, handler, sample_job, mock_processor, mock_request
    ):
        """Test get_validation_status when no change tracking data is available."""
        # Create combined results without change tracking
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, error_types={}, columns_validated=0),
        )

        combined_results_without_tracking = CombinedResults(
            validation_results=validation_results, schema_alignment_results=None, change_tracking=None
        )

        # Setup mocks
        handler.job_status_saver.get_job.return_value = sample_job
        handler.processor_manager.get_processor.return_value = mock_processor
        handler.processor_manager.cleanup_processor.return_value = None
        mock_processor.data_saver.get_results.return_value = combined_results_without_tracking

        # Call the method
        response = await handler.get_validation_status(metadata_id=UUID(sample_job.job_id), request=mock_request)

        # Verify response structure
        assert isinstance(response, ValidationStatusResponse)
        assert response.latest_results is not None
        assert response.latest_results.change_tracking is None

    @pytest.mark.asyncio
    async def test_get_validation_status_pending_job_no_change_tracking(self, handler, mock_request):
        """Test get_validation_status for pending job (no change tracking expected)."""
        # Create a pending job
        pending_job = MetadataUploadJob(
            job_id=str(uuid4()),
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=None,
            current_version=1,
            results={},
        )

        # Setup mocks
        handler.job_status_saver.get_job.return_value = pending_job

        # Call the method
        response = await handler.get_validation_status(metadata_id=UUID(pending_job.job_id), request=mock_request)

        # Verify response structure
        assert isinstance(response, ValidationStatusResponse)
        assert response.status == "pending"
        assert response.latest_results is None

    @pytest.mark.asyncio
    async def test_change_tracking_serialization_camel_case(
        self, handler, sample_job, sample_processor_combined_results, mock_processor, mock_request
    ):
        """Test that change tracking data is properly serialized with camelCase aliases."""
        # Setup mocks
        handler.job_status_saver.get_job.return_value = sample_job
        handler.processor_manager.get_processor.return_value = mock_processor
        handler.processor_manager.cleanup_processor.return_value = None
        mock_processor.data_saver.get_results.return_value = sample_processor_combined_results

        # Call the method
        response = await handler.get_validation_status(metadata_id=UUID(sample_job.job_id), request=mock_request)

        # Serialize with camelCase aliases
        response_data = response.model_dump(by_alias=True)

        # Verify camelCase serialization
        assert "latestResults" in response_data
        assert "changeTracking" in response_data["latestResults"]

        change_tracking_data = response_data["latestResults"]["changeTracking"]
        assert "changes" in change_tracking_data
        assert "summary" in change_tracking_data
        assert "comparisonMetadata" in change_tracking_data

        # Verify change object camelCase fields
        first_change = change_tracking_data["changes"][0]
        expected_camel_case_fields = {
            "changeId",
            "changeType",
            "sourceType",
            "component",
            "column",
            "row",
            "oldValue",
            "newValue",
            "timestamp",
            "sourceVersion",
            "targetVersion",
            "confidenceScore",
            "userContext",
        }

        # Check that camelCase fields are present (some may be None)
        for field in expected_camel_case_fields:
            assert field in first_change

        # Verify summary camelCase fields
        summary_data = change_tracking_data["summary"]
        assert "totalChanges" in summary_data
        assert "systemChanges" in summary_data
        assert "userChanges" in summary_data

    @pytest.mark.asyncio
    async def test_change_tracking_error_handling(self, handler, sample_job, mock_processor, mock_request):
        """Test error handling when change tracking data loading fails."""
        # Setup mocks to simulate error in loading results
        handler.job_status_saver.get_job.return_value = sample_job
        handler.processor_manager.get_processor.return_value = mock_processor
        handler.processor_manager.cleanup_processor.return_value = None
        mock_processor.data_saver.get_results.side_effect = Exception("Failed to load results")

        # Call the method - should not raise exception
        response = await handler.get_validation_status(metadata_id=UUID(sample_job.job_id), request=mock_request)

        # Verify response structure (should still work without results)
        assert isinstance(response, ValidationStatusResponse)
        assert response.status == "completed"
        assert response.latest_results is None  # Results should be None due to error

    @pytest.mark.asyncio
    async def test_backward_compatibility_without_change_tracking(
        self, handler, sample_job, mock_processor, mock_request
    ):
        """Test backward compatibility when processor doesn't have change tracking."""
        # Create old-style combined results without change tracking
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1, column="test_column", current_value="test", error_type=ValidationErrorType.REQUIRED_VALUE
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=1, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        # Create combined results without change_tracking attribute (simulating old version)
        old_combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=None,
            # Note: no change_tracking field
        )

        # Setup mocks
        handler.job_status_saver.get_job.return_value = sample_job
        handler.processor_manager.get_processor.return_value = mock_processor
        handler.processor_manager.cleanup_processor.return_value = None
        mock_processor.data_saver.get_results.return_value = old_combined_results

        # Call the method
        response = await handler.get_validation_status(metadata_id=UUID(sample_job.job_id), request=mock_request)

        # Verify response works without change tracking
        assert isinstance(response, ValidationStatusResponse)
        assert response.latest_results is not None
        assert response.latest_results.validation_results is not None
        assert response.latest_results.change_tracking is None

        # Verify validation results are still included
        assert len(response.latest_results.validation_results.validation_results) == 1


class TestChangeTrackingModelConversion:
    """Test cases for converting processor change tracking models to API models."""

    def test_processor_to_api_change_object_conversion(self):
        """Test conversion from processor ChangeObject to API ChangeObject."""
        # The API uses processor models directly (no separate API models)
        APIChangeObject = ChangeObject

        # Create processor change object
        processor_change = ChangeObject(
            change_id="chg_test_001",
            change_type="rename",
            source_type="system",
            component="validation",
            column="B2",
            row=2,
            old_value="old_name",
            new_value="new_name",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.9,
            user_context={"note": "test conversion"},
        )

        # Convert to API model
        api_change = APIChangeObject(
            change_id=processor_change.change_id,
            change_type=processor_change.change_type,
            source_type=processor_change.source_type,
            component=processor_change.component,
            column=processor_change.column,
            row=processor_change.row,
            old_value=processor_change.old_value,
            new_value=processor_change.new_value,
            timestamp=processor_change.timestamp,
            source_version=processor_change.source_version,
            target_version=processor_change.target_version,
            confidence_score=processor_change.confidence_score,
            user_context=processor_change.user_context,
        )

        # Verify conversion
        assert api_change.change_id == "chg_test_001"
        assert api_change.change_type == "rename"
        assert api_change.source_type == "system"
        assert api_change.component == "validation"
        assert api_change.column == "B2"
        assert api_change.row == processor_change.row
        assert api_change.old_value == "old_name"
        assert api_change.new_value == "new_name"
        assert api_change.confidence_score == 0.9
        assert api_change.user_context == {"note": "test conversion"}

    def test_processor_to_api_changes_summary_conversion(self):
        """Test conversion from processor ChangesSummary to API ChangesSummary."""
        APIChangesSummary = ChangesSummary

        # Create processor summary
        processor_summary = ChangesSummary(
            total_changes=5, adds=2, removes=1, renames=2, system_changes=3, user_changes=2
        )

        # Convert to API model
        api_summary = APIChangesSummary(
            total_changes=processor_summary.total_changes,
            adds=processor_summary.adds,
            removes=processor_summary.removes,
            renames=processor_summary.renames,
            system_changes=processor_summary.system_changes,
            user_changes=processor_summary.user_changes,
        )

        # Verify conversion
        assert api_summary.total_changes == 5
        assert api_summary.adds == 2
        assert api_summary.removes == 1
        assert api_summary.renames == 2
        assert api_summary.system_changes == 3
        assert api_summary.user_changes == 2

    def test_processor_to_api_change_tracking_results_conversion(self):
        """Test conversion from processor ChangeTrackingResults to API ChangeTrackingResults."""
        APIChangeTrackingResults = ChangeTrackingResults
        APIChangeObject = ChangeObject
        APIChangesSummary = ChangesSummary

        # Create processor change tracking results
        processor_changes = [
            ChangeObject(
                change_id="chg_001",
                change_type="add",
                source_type="system",
                component="validation",
                column="A1",
                row=1,
                new_value="test_value",
                timestamp="2025-01-01T12:00:00Z",
                source_version=1,
                target_version=2,
                confidence_score=0.8,
            )
        ]

        processor_summary = ChangesSummary(
            total_changes=1, adds=1, removes=0, renames=0, system_changes=1, user_changes=0
        )

        processor_tracking = ChangeTrackingResults(
            changes=processor_changes, summary=processor_summary, comparison_metadata={"test": "metadata"}
        )

        # Convert to API models
        api_changes = [
            APIChangeObject(
                change_id=change.change_id,
                change_type=change.change_type,
                source_type=change.source_type,
                component=change.component,
                column=change.column,
                row=change.row,
                old_value=change.old_value,
                new_value=change.new_value,
                timestamp=change.timestamp,
                source_version=change.source_version,
                target_version=change.target_version,
                confidence_score=change.confidence_score,
                user_context=change.user_context,
            )
            for change in processor_tracking.changes
        ]

        api_summary = APIChangesSummary(
            total_changes=processor_tracking.summary.total_changes,
            adds=processor_tracking.summary.adds,
            removes=processor_tracking.summary.removes,
            renames=processor_tracking.summary.renames,
            system_changes=processor_tracking.summary.system_changes,
            user_changes=processor_tracking.summary.user_changes,
        )

        api_tracking = APIChangeTrackingResults(
            changes=api_changes, summary=api_summary, comparison_metadata=processor_tracking.comparison_metadata
        )

        # Verify conversion
        assert len(api_tracking.changes) == 1
        assert api_tracking.changes[0].change_id == "chg_001"
        assert api_tracking.summary.total_changes == 1
        assert api_tracking.comparison_metadata == {"test": "metadata"}
