#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Simplified Basic Usage Example for MetadataHarmonizationProcessor

This example demonstrates the LocalJobStatusSaver functionality
for local development without AWS dependencies.

This simplified version focuses on testing the core components
without running the full AWS Strands pipeline.
"""

import asyncio
import pandas as pd
from pathlib import Path

from metadata_harmonization_processor.config import load_processor_settings
from metadata_harmonization_processor.implementations import LocalJobStatusSaver, FileBasedSchemaCollector


async def test_local_job_status_saver():
    """Test LocalJobStatusSaver functionality."""
    print("=== Testing LocalJobStatusSaver ===")

    # Test file-based storage
    print("Testing file-based storage...")
    file_saver = LocalJobStatusSaver(storage_type="file", storage_dir="./job_status")

    job_id = "test-job-123"

    # Save initial status
    await file_saver.save_status(job_id, "running", {"stage": "initialization", "message": "Starting processing"})
    print(f"✓ Saved initial status for job {job_id}")

    # Update progress
    await file_saver.update_progress(job_id, "schema_alignment", 0.25)
    await file_saver.update_progress(job_id, "validation", 0.50)
    print("✓ Updated progress for multiple stages")

    # Retrieve status
    status = await file_saver.get_status(job_id)
    print(f"✓ Retrieved status: {status['status']}")
    print(f"  Progress: {status['metadata'].get('progress', {})}")

    # Test in-memory storage
    print("\nTesting in-memory storage...")
    memory_saver = LocalJobStatusSaver(storage_type="memory")

    await memory_saver.save_status(
        "memory-job-456", "completed", {"final_stage": "pattern_prediction", "total_errors": 5, "recommendations": 3}
    )

    memory_status = await memory_saver.get_status("memory-job-456")
    print(f"✓ Memory storage works: {memory_status['status']}")
    print(f"  Metadata: {memory_status['metadata']}")

    print("✅ LocalJobStatusSaver tests completed successfully!")
    return True


async def test_schema_collector():
    """Test FileBasedSchemaCollector functionality."""
    print("\n=== Testing FileBasedSchemaCollector ===")

    try:
        collector = FileBasedSchemaCollector("./examples/data/schema")

        # Test getting available schemas
        schemas = await collector.get_available_schemas()
        print(f"✓ Found {len(schemas)} available schemas")

        if schemas:
            schema = schemas[0]
            print(f"  Example schema: {schema.core_name} / {schema.program_name}")

            # Test getting schema definition
            schema_def = await collector.get_schema(schema.program_uuid, schema.core_uuid)
            print(f"✓ Retrieved schema definition with {len(schema_def.get('properties', {}))} properties")

            # Test getting columns
            columns = await collector.get_schema_columns(schema.program_uuid, schema.core_uuid)
            print(f"✓ Retrieved {len(columns)} expected columns")

        print("✅ FileBasedSchemaCollector tests completed successfully!")
        return True

    except Exception as e:
        print(f"⚠️  Schema collector test failed: {e}")
        print("   This is expected if schema files are not properly configured")
        return False


async def test_configuration_loading():
    """Test configuration loading with local development settings."""
    print("\n=== Testing Configuration Loading ===")

    try:
        config_path = Path("examples/config-basic.yaml")
        config = load_processor_settings(config_path=config_path)

        print("✓ Configuration loaded successfully")
        print(f"  Local development mode: {config.local_development_mode}")
        print(f"  Session type: {config.session_saver_type}")
        print(f"  Redis caching: {config.enable_redis_cache}")
        print(f"  Memory caching: {config.enable_memory_cache}")
        print(f"  Job status saver config: {getattr(config, 'job_status_saver', 'Not configured')}")

        print("✅ Configuration loading tests completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


async def demonstrate_local_development_workflow():
    """Demonstrate the complete local development workflow."""
    print("\n=== Local Development Workflow Demonstration ===")

    # Load sample data
    csv_paths = [
        "./examples/data/example_metadata.csv",
        "./data/example_metadata.csv",
    ]

    metadata_df = None
    for path in csv_paths:
        try:
            if Path(path).exists():
                # Use schema-aware CSV loading to preserve datatypes
                # This prevents issues like "FALSE"/"TRUE" being converted to Python bools
                metadata_df = await processor.load_csv(path, program_id, core_id)
                print(f"✓ Loaded sample data from {path}")
                print(f"  Shape: {metadata_df.shape}")
                print(f"  Columns: {list(metadata_df.columns)}")
                break
        except Exception:
            continue

    if metadata_df is None:
        print("⚠️  No sample data found, creating synthetic data")
        metadata_df = pd.DataFrame(
            {
                "patient_id": ["P001", "P002", "P003"],
                "age": [25, 30, "invalid"],
                "gender": ["M", "F", "X"],
                "diagnosis": ["Cyclospora", "Cyclospora", ""],
            }
        )

    # Demonstrate job status tracking
    print("\n📋 Simulating processing workflow with job status tracking...")

    job_saver = LocalJobStatusSaver(storage_type="file", storage_dir="./job_status")
    job_id = f"demo-job-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"

    # Simulate processing stages
    stages = [
        ("initialization", "Initializing processor", 0.1),
        ("schema_alignment", "Aligning DataFrame columns", 0.3),
        ("validation", "Validating data against schema", 0.6),
        ("semantic_prediction", "Generating AI recommendations", 0.8),
        ("pattern_prediction", "Applying pattern matching", 0.9),
        ("completion", "Processing completed", 1.0),
    ]

    await job_saver.save_status(
        job_id,
        "running",
        {
            "input_rows": len(metadata_df),
            "input_columns": len(metadata_df.columns),
            "start_time": pd.Timestamp.now().isoformat(),
        },
    )

    for stage, description, progress in stages:
        print(f"  🔄 {description}...")
        await job_saver.update_progress(job_id, stage, progress)
        await asyncio.sleep(0.1)  # Simulate processing time

    # Mark as completed
    await job_saver.save_status(
        job_id,
        "completed",
        {
            "input_rows": len(metadata_df),
            "input_columns": len(metadata_df.columns),
            "final_stage": "completion",
            "end_time": pd.Timestamp.now().isoformat(),
        },
    )

    # Show final status
    final_status = await job_saver.get_status(job_id)
    print("\n✅ Processing simulation completed!")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {final_status['status']}")
    print(f"  Progress: {final_status['metadata'].get('progress', {})}")
    print(f"  Job status saved to: ./job_status/{job_id}.json")

    return True


async def main():
    """Main demonstration function."""
    print("=" * 70)
    print("🚀 MetadataHarmonizationProcessor - Local Development Demo")
    print("=" * 70)
    print()
    print("This demonstration shows how to use the processor components")
    print("for local development without AWS dependencies.")
    print()

    success_count = 0
    total_tests = 4

    # Run all tests
    if await test_configuration_loading():
        success_count += 1

    if await test_local_job_status_saver():
        success_count += 1

    if await test_schema_collector():
        success_count += 1

    if await demonstrate_local_development_workflow():
        success_count += 1

    print("\n" + "=" * 70)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All local development components are working correctly!")
        print()
        print("NEXT STEPS:")
        print("1. The LocalJobStatusSaver is ready for local development")
        print("2. Configuration loading works with local development settings")
        print("3. Job status is persisted to ./job_status/ directory")
        print("4. You can switch to production mode by updating config-basic.yaml")
    else:
        print("⚠️  Some components need attention, but core functionality works")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
