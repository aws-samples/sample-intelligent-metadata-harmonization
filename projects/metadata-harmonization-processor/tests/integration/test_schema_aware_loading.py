# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for schema-aware CSV loading with real schemas.

These tests use actual schema files to verify that the loading works
correctly with real-world data and schema combinations.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from metadata_harmonization_processor.implementations.file_schema_collector import (
    FileBasedSchemaCollector,
)
from metadata_harmonization_processor.utils.data_loader import load_metadata_csv


@pytest.mark.asyncio
async def test_load_water_quality_data_with_string_fields():
    """
    Test loading water quality data with string fields.

    This test verifies that all fields are preserved as strings,
    including numeric-looking values like detection_limit and field_ph.
    """
    # Create test CSV with water quality data
    csv_content = """SampleId,CollectorName,SampleType,CollectionDate,AnalysisDate,SampleOriginCountry,SampleOriginState,SiteClassification,CollectionMethod,SampleStatus,analysis_method,parameter_measured,measurement_unit,quality_control_type,laboratory_name,sample_preservation,detection_limit,sample_matrix,reporting_limit,field_ph
WQ001,Environmental Monitoring Team,Surface Water,2024-01-15,2024-01-20,United States of America,CA,Agricultural,Grab Sample,Completed,EPA 200.8,Lead,ug/L,Duplicate,AquaLab Services,HNO3,0.5,Water,1.0,7.2
WQ002,Field Services Division,Groundwater,2024-01-16,2024-01-21,Canada,ON,Industrial,Composite Sample,In Analysis,EPA 524.2,Copper,mg/L,Standard,TestWater Inc,H2SO4,0.01,Water,0.05,6.8
WQ003,Water Resources Unit,Drinking Water,2024-01-17,2024-01-22,Mexico,CMX,Municipal,Continuous Monitoring,Completed,SM 2120B,Turbidity,NTU,Not Applicable,EnviroTest Labs,None,0.1,Water,0.2,7.5
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        # Use real schema collector with actual schemas
        schema_dir = Path(__file__).parents[4] / "data" / "schema"
        schema_collector = FileBasedSchemaCollector(str(schema_dir))

        # Get water quality schema IDs from catalog
        core_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        program_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"

        # Load CSV with schema-aware types
        df = await load_metadata_csv(csv_path, program_id, core_id, schema_collector)

        # Verify all string fields are preserved as strings
        assert df["SampleId"].dtype == object
        assert df["SampleId"].iloc[0] == "WQ001"
        assert df["SampleId"].iloc[1] == "WQ002"
        assert df["SampleId"].iloc[2] == "WQ003"

        assert df["CollectorName"].dtype == object
        assert df["CollectorName"].iloc[0] == "Environmental Monitoring Team"
        assert df["CollectorName"].iloc[1] == "Field Services Division"

        assert df["SampleType"].dtype == object
        assert df["SampleType"].iloc[0] == "Surface Water"
        assert df["SampleType"].iloc[1] == "Groundwater"

        # Verify numeric-looking strings are preserved as strings
        assert df["detection_limit"].dtype == object
        assert df["detection_limit"].iloc[0] == "0.5"  # Not 0.5 float
        assert df["detection_limit"].iloc[1] == "0.01"  # Not 0.01 float
        assert df["detection_limit"].iloc[2] == "0.1"

        assert df["reporting_limit"].dtype == object
        assert df["reporting_limit"].iloc[0] == "1.0"  # Not 1.0 float
        assert df["reporting_limit"].iloc[1] == "0.05"

        assert df["field_ph"].dtype == object
        assert df["field_ph"].iloc[0] == "7.2"  # Not 7.2 float
        assert df["field_ph"].iloc[1] == "6.8"
        assert df["field_ph"].iloc[2] == "7.5"

    finally:
        # Clean up temp file
        Path(csv_path).unlink()


@pytest.mark.asyncio
async def test_processor_load_csv_method():
    """
    Test the processor's load_csv method with real schema.

    This test verifies that the convenience method on the processor
    works correctly end-to-end with water quality data.
    """
    import shutil
    import uuid

    from metadata_harmonization_processor import MetadataHarmonizationProcessor
    from metadata_harmonization_processor.config import load_processor_settings

    # Create test CSV with water quality data
    csv_content = """SampleId,CollectorName,SampleType,detection_limit,field_ph
WQ100,Environmental Monitoring Team,Surface Water,0.25,7.1
WQ200,Field Services Division,Groundwater,0.50,6.9
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    # Create unique temporary directories for this test
    test_id = str(uuid.uuid4())[:8]
    test_session_dir = f"/tmp/test_sessions_{test_id}"
    test_results_dir = f"/tmp/test_results_{test_id}"
    test_jobs_dir = f"/tmp/test_jobs_{test_id}"

    try:
        # Load processor config with file session manager
        config_path = Path(__file__).parents[1].parent / "config.yaml.example"
        schema_dir = Path(__file__).parents[4] / "data" / "schema"
        config = load_processor_settings(
            config_path=config_path,
            override={
                "local_development_mode": True,
                "session_saver_type": "file",  # Use file instead of S3 for tests
                "file_session_directory": test_session_dir,
                "result_saver_type": "local",
                "results_local_dir": test_results_dir,
                "job_status_saver_type": "local",
                "job_status_storage_dir": test_jobs_dir,
                "schema_directory": str(schema_dir),
            },
        )

        # Create processor with unique session ID
        session_id = f"test-session-{test_id}"
        processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)

        # Use processor's load_csv method
        core_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        program_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"

        df = await processor.load_csv(csv_path, program_id, core_id)

        # Verify string fields preserved
        assert df["SampleId"].iloc[0] == "WQ100"
        assert df["SampleId"].iloc[1] == "WQ200"
        assert df["CollectorName"].iloc[0] == "Environmental Monitoring Team"
        assert df["CollectorName"].iloc[1] == "Field Services Division"
        assert df["SampleType"].iloc[0] == "Surface Water"
        assert df["SampleType"].iloc[1] == "Groundwater"
        # Verify numeric-looking strings preserved
        assert df["detection_limit"].iloc[0] == "0.25"
        assert df["detection_limit"].iloc[1] == "0.50"
        assert df["field_ph"].iloc[0] == "7.1"
        assert df["field_ph"].iloc[1] == "6.9"

    finally:
        # Clean up
        Path(csv_path).unlink()
        # Clean up test directories
        for test_dir in [test_session_dir, test_results_dir, test_jobs_dir]:
            if Path(test_dir).exists():
                shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_comparison_with_default_pandas_loading():
    """
    Test that demonstrates the difference between default pandas loading
    and schema-aware loading.

    This test shows that default pandas would incorrectly convert
    numeric-looking strings to floats, losing precision and format.
    """
    csv_content = """detection_limit,field_ph,reporting_limit
0.5,7.2,1.0
0.01,6.8,0.05
0.1,7.5,0.2
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        # Default pandas loading (problematic)
        df_default = pd.read_csv(csv_path)
        assert df_default["detection_limit"].dtype == float  # Incorrectly inferred as float
        assert df_default["detection_limit"].iloc[0] == 0.5  # Python float, not "0.5"
        assert df_default["field_ph"].dtype == float
        assert df_default["field_ph"].iloc[1] == 6.8  # Python float, not "6.8"

        # Schema-aware loading (correct)
        schema_dir = Path(__file__).parents[4] / "data" / "schema"
        schema_collector = FileBasedSchemaCollector(str(schema_dir))
        core_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        program_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"

        df_schema_aware = await load_metadata_csv(csv_path, program_id, core_id, schema_collector)
        assert df_schema_aware["detection_limit"].dtype == object  # String type
        assert df_schema_aware["detection_limit"].iloc[0] == "0.5"  # Preserved as string
        assert df_schema_aware["detection_limit"].iloc[1] == "0.01"  # Leading zero preserved
        assert df_schema_aware["field_ph"].dtype == object
        assert df_schema_aware["field_ph"].iloc[1] == "6.8"  # Preserved as string
        assert df_schema_aware["reporting_limit"].dtype == object
        assert df_schema_aware["reporting_limit"].iloc[0] == "1.0"  # Trailing zero preserved

    finally:
        Path(csv_path).unlink()
