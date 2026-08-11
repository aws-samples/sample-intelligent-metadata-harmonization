#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Result Retrieval Example for MetadataHarmonizationProcessor

This example demonstrates how to retrieve and list saved ValidationResults
using both LocalResultSaver and S3ResultSaver implementations.

Features demonstrated:
- Listing all result versions for a job
- Retrieving specific results by JobResults location
- Working with both local and S3 storage backends
- Handling result metadata and version tracking
"""

import asyncio
import pandas as pd
from pathlib import Path

from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings


async def demonstrate_local_result_retrieval():
    """Demonstrate result retrieval with LocalResultSaver."""
    print("=== Local Result Retrieval Demo ===")

    # Load local configuration
    config = load_processor_settings(config_path=Path("examples/config-local.yaml"))

    # Initialize processor with local storage
    session_id = f"retrieval-demo-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)

    try:
        # Create sample data for processing
        sample_data = pd.DataFrame(
            {
                "patient_id": ["P001", "P002", "INVALID_ID"],
                "age": [25, 30, "invalid_age"],
                "gender": ["M", "F", "X"],
                "status": ["active", "inactive", ""],
            }
        )

        print(f"Processing {len(sample_data)} rows of sample data...")

        # Process data to generate results
        results = await processor.process(metadata_df=sample_data, program_id="example-program", core_id="example-core")

        # Get the job ID from processor state
        state = processor.get_current_state()
        job_id = state.job_id if state else "unknown"

        print(f"✓ Processing completed. Job ID: {job_id}")
        print(f"  Total errors found: {results.summary.total_errors}")

        # Access the result saver for retrieval operations
        result_saver = processor.data_saver.result_saver

        # Demonstrate result listing
        print(f"\n📋 Listing all results for job {job_id}:")
        all_results = await result_saver.list_results(job_id)

        if all_results:
            for i, job_result in enumerate(all_results):
                print(f"  Version {job_result.version}:")
                print(f"    Storage Type: {job_result.storage_type}")
                print(f"    Location: {job_result.location}")
                print(f"    Created: {job_result.created_at}")
                if job_result.metadata:
                    print(f"    Metadata: {job_result.metadata}")
        else:
            print("  No results found for this job")

        # Demonstrate result retrieval
        if all_results:
            print(f"\n🔍 Retrieving results for version {all_results[0].version}:")
            retrieved_results = await result_saver.get_results(all_results[0])

            if retrieved_results:
                print("  ✓ Successfully retrieved ValidationResults")
                print(f"    Total rows: {retrieved_results.summary.total_rows}")
                print(f"    Total errors: {retrieved_results.summary.total_errors}")
                print(f"    Error types: {retrieved_results.summary.error_types}")

                # Show sample validation errors
                if retrieved_results.validation_results:
                    print("    Sample errors:")
                    for error in retrieved_results.validation_results[:3]:
                        print(f"      Row {error.row}, Column '{error.column}': {error.error_type}")
                        if error.recommended_value:
                            print(f"        Recommendation: '{error.recommended_value}'")
            else:
                print("  ✗ Failed to retrieve results")

        # Demonstrate saving additional versions
        print("\n💾 Saving additional result version...")

        # Modify some data and process again for version 2
        sample_data_v2 = sample_data.copy()
        sample_data_v2.loc[0, "age"] = "another_invalid_age"

        # Reset processor state for new processing
        processor.reset_state()

        await processor.process(metadata_df=sample_data_v2, program_id="example-program", core_id="example-core")

        # List results again to show multiple versions
        state_v2 = processor.get_current_state()
        job_id_v2 = state_v2.job_id if state_v2 else "unknown"

        print(f"✓ Version 2 processing completed. Job ID: {job_id_v2}")

        # Show all versions for the new job
        all_results_v2 = await result_saver.list_results(job_id_v2)
        print(f"📋 Job {job_id_v2} now has {len(all_results_v2)} result versions")

    except Exception as e:
        print(f"❌ Error during local result retrieval demo: {e}")

    finally:
        await processor.cleanup()


async def demonstrate_s3_result_retrieval():
    """Demonstrate result retrieval with S3ResultSaver."""
    print("\n=== S3 Result Retrieval Demo ===")

    try:
        # Load S3 configuration
        config = load_processor_settings(config_path=Path("examples/config-s3.yaml"))

        # Initialize processor with S3 storage
        session_id = f"s3-retrieval-demo-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
        processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)

        # Create sample data
        sample_data = pd.DataFrame(
            {"patient_id": ["P001", "P002"], "age": [25, "invalid"], "email": ["user@example.com", "invalid-email"]}
        )

        print(f"Processing {len(sample_data)} rows with S3 storage...")

        # Process data
        await processor.process(metadata_df=sample_data, program_id="s3-example-program", core_id="s3-example-core")

        # Get job ID
        state = processor.get_current_state()
        job_id = state.job_id if state else "unknown"

        print(f"✓ S3 processing completed. Job ID: {job_id}")
        print(f"  Results stored in S3 bucket: {config.results_s3_bucket}")
        print(f"  S3 prefix: {config.results_s3_prefix}")

        # Access S3 result saver
        result_saver = processor.data_saver.result_saver

        # List S3 results
        print(f"\n📋 Listing S3 results for job {job_id}:")
        s3_results = await result_saver.list_results(job_id)

        for job_result in s3_results:
            print(f"  Version {job_result.version}:")
            print(f"    S3 Bucket: {job_result.bucket}")
            print(f"    S3 Key: {job_result.location}")
            print(f"    Storage Type: {job_result.storage_type}")

        # Retrieve from S3
        if s3_results:
            print("\n🔍 Retrieving results from S3...")
            s3_retrieved = await result_saver.get_results(s3_results[0])

            if s3_retrieved:
                print("  ✓ Successfully retrieved from S3")
                print(f"    Total errors: {s3_retrieved.summary.total_errors}")
            else:
                print("  ✗ Failed to retrieve from S3")

        await processor.cleanup()

    except Exception as e:
        print(f"❌ S3 result retrieval demo failed: {e}")
        print("  Note: This requires valid AWS credentials and S3 bucket access")
        print("  Make sure your AWS credentials are configured and the S3 bucket exists")


async def demonstrate_result_comparison():
    """Demonstrate comparing results across different versions."""
    print("\n=== Result Version Comparison Demo ===")

    # Use local storage for this demo
    config = load_processor_settings(config_path=Path("examples/config-local.yaml"))

    session_id = f"comparison-demo-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)

    try:
        # Create base dataset
        base_data = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "name": ["John Doe", "jane smith", ""],
                "email": ["john@example.com", "invalid-email", "user@domain.com"],
                "age": [25, "thirty", 45],
            }
        )

        # Process version 1
        print("Processing version 1 (original data)...")
        results_v1 = await processor.process(
            metadata_df=base_data, program_id="comparison-program", core_id="comparison-core"
        )

        state_v1 = processor.get_current_state()
        job_id = state_v1.job_id if state_v1 else "unknown"

        # Process version 2 with some corrections
        processor.reset_state()
        corrected_data = base_data.copy()
        corrected_data.loc[1, "name"] = "Jane Smith"  # Fix name casing
        corrected_data.loc[2, "name"] = "Bob Johnson"  # Fill missing name

        print("Processing version 2 (partially corrected data)...")
        results_v2 = await processor.process(
            metadata_df=corrected_data, program_id="comparison-program", core_id="comparison-core"
        )

        state_v2 = processor.get_current_state()
        job_id_v2 = state_v2.job_id if state_v2 else "unknown"

        # Compare results
        result_saver = processor.data_saver.result_saver

        # Get all versions for comparison
        all_versions_v1 = await result_saver.list_results(job_id)
        all_versions_v2 = await result_saver.list_results(job_id_v2)

        print("\n📊 Result Comparison:")
        print(f"  Job 1 ({job_id}): {len(all_versions_v1)} versions")
        print(f"    Total errors: {results_v1.summary.total_errors}")
        print(f"    Error types: {results_v1.summary.error_types}")

        print(f"  Job 2 ({job_id_v2}): {len(all_versions_v2)} versions")
        print(f"    Total errors: {results_v2.summary.total_errors}")
        print(f"    Error types: {results_v2.summary.error_types}")

        # Show improvement
        error_reduction = results_v1.summary.total_errors - results_v2.summary.total_errors
        if error_reduction > 0:
            print(f"  📈 Improvement: {error_reduction} fewer errors in version 2")
        elif error_reduction < 0:
            print(f"  📉 Regression: {abs(error_reduction)} more errors in version 2")
        else:
            print("  ➡️  No change in error count between versions")

    except Exception as e:
        print(f"❌ Error during comparison demo: {e}")

    finally:
        await processor.cleanup()


async def main():
    """Run all result retrieval demonstrations."""
    print("🔍 MetadataHarmonizationProcessor - Result Retrieval Examples")
    print("=" * 70)

    # Run local result retrieval demo
    await demonstrate_local_result_retrieval()

    # Run S3 result retrieval demo (may fail without AWS credentials)
    await demonstrate_s3_result_retrieval()

    # Run result comparison demo
    await demonstrate_result_comparison()

    print("\n✅ All result retrieval demonstrations completed!")
    print("\n💡 Key Takeaways:")
    print("  - Results are automatically saved during processing")
    print("  - Multiple versions can be stored per job ID")
    print("  - Both local and S3 storage support full retrieval operations")
    print("  - JobResults contain metadata for tracking and organization")
    print("  - Use list_results() to find all versions, get_results() to retrieve specific versions")
    print("\n🧪 Integration Testing:")
    print("  - Comprehensive integration tests validate all storage scenarios")
    print("  - Run 'pytest tests/integration/test_end_to_end_pipeline.py -k result_storage' to test storage backends")
    print("  - Tests cover error recovery, version tracking, and DataSaver coordination")
    print("  - See docs/RESULT_STORAGE_TROUBLESHOOTING.md for detailed testing information")


if __name__ == "__main__":
    asyncio.run(main())
