#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Basic Usage Example for MetadataHarmonizationProcessor

This example demonstrates the simplest way to use the processor
with minimal configuration and built-in implementations for local development.

⚠️  CURRENT STATUS: This example has AWS Strands integration issues that are being resolved.
    For a working demonstration of LocalJobStatusSaver and local development features,
    please run: python examples/basic_usage_simple.py

LOCAL DEVELOPMENT SETUP:
- Uses LocalJobStatusSaver with file-based storage for persistence across runs
- Uses FileBasedSchemaCollector to read schemas from local directory
- Disables Redis caching and uses in-memory caching instead
- Works without AWS credentials or cloud services when local_development_mode=true
- Job status is persisted to ./job_status/ directory as JSON files
- Session data is stored in ./sessions/ directory

CONFIGURATION:
- Edit config-basic.yaml to customize settings
- Set job_status_saver.type to "local" for local development
- Set job_status_saver.type to "dynamodb" for production with AWS
- Update schema_directory path to point to your local schema files

WORKING DEMO:
- Run `python examples/basic_usage_simple.py` for a working demonstration
- This shows LocalJobStatusSaver, configuration loading, and schema collection
- All local development features work correctly without AWS dependencies
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path

from metadata_harmonization_processor.processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings

# Configure logging to see processor debug information
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Set specific loggers to INFO level to see our debug messages
logging.getLogger("metadata_harmonization_processor").setLevel(logging.INFO)
logging.getLogger("metadata_harmonization_processor.processor").setLevel(logging.INFO)


def display_configuration_info(config):
    """Display information about the configuration-driven setup.

    This function shows how the processor automatically creates components
    based on configuration settings, eliminating the need for manual setup.

    Args:
        config: Processor configuration loaded from YAML
    """
    print("📋 Configuration-Driven Setup:")
    print(f"  - Job Status Saver: {config.job_status_saver_type}")
    if config.job_status_saver_type == "local":
        print(f"    Storage Directory: {config.job_status_storage_dir}")
        print("    🏠 Local development mode - no AWS credentials required!")
    else:
        print(f"    DynamoDB Table: {config.job_status_table_name}")
        print("    ☁️  Production mode - requires AWS credentials")

    print(f"  - Result Saver: {config.result_saver_type}")
    if config.result_saver_type == "local":
        print(f"    Storage Directory: {config.results_local_dir}")
        print("    📁 Results saved as JSON files with version tracking")
    else:
        print(f"    S3 Bucket: {config.results_s3_bucket}")
        print(f"    S3 Prefix: {config.results_s3_prefix}")

    print("  - Schema Collector: FileBasedSchemaCollector")
    print(f"    Schema Directory: {config.schema_directory}")
    print()


async def main():
    """Basic usage example with configuration-driven local development setup."""

    print("=== MetadataHarmonizationProcessor Basic Usage Example ===")
    print("This example demonstrates local development without AWS dependencies\n")

    # Load configuration first
    config_path = Path("examples/config-basic.yaml")
    print(f"Loading configuration from: {config_path}")

    try:
        config = load_processor_settings(config_path=config_path)
        print("✓ Configuration loaded successfully")
        print(f"  - Local development mode: {config.local_development_mode}")
        print(f"  - Session type: {config.session_saver_type}")
        print(f"  - Redis caching: {config.enable_redis_cache}")
        print(f"  - Memory caching: {config.enable_memory_cache}")
        print()
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        return

    # Load sample metadata from CSV file
    # Try multiple possible locations for the CSV file
    possible_csv_paths = [
        "./examples/data/example_metadata.csv",  # Example dataset with validation errors
        "./data/example_metadata.csv",
        "./data/Realistic Cyclospora Metadata 1.csv",  # Original dataset if available
        "../data/Realistic Cyclospora Metadata 1.csv",
        "../../data/Realistic Cyclospora Metadata 1.csv",
    ]

    metadata_df = None
    csv_path = None

    for path in possible_csv_paths:
        try:
            if Path(path).exists():
                # Use schema-aware CSV loading to preserve datatypes
                # This prevents issues like "FALSE"/"TRUE" being converted to Python bools
                metadata_df = await processor.load_csv(path, program_id, core_id)
                csv_path = path
                break
        except Exception:
            continue

    if metadata_df is None:
        # Create sample data if no CSV file found
        print("No sample CSV file found, creating synthetic metadata for demonstration")
        print("💡 Tip: Use the provided example_metadata.csv for a complete demonstration")
        metadata_df = pd.DataFrame(
            {
                "patient_id": ["P001", "P002", "INVALID_ID"],
                "age": [25, 30, "invalid_age"],
                "gender": ["M", "F", "X"],
                "diagnosis": ["Cyclospora", "Cyclospora", ""],
                "collection_date": ["2023-01-15", "2023-01-16", "invalid_date"],
            }
        )
        csv_path = "synthetic_data"

    print(f"✓ Loaded {len(metadata_df)} rows from {csv_path}")
    print(f"  Columns: {list(metadata_df.columns)}")

    if "example_metadata.csv" in csv_path:
        print("  📋 This dataset contains intentional validation errors for demonstration")
        print("     See examples/data/DATASET_INFO.md for details about each validation scenario")

    print("\nFirst few rows:")
    print(metadata_df.head())
    print()

    # Display configuration information
    display_configuration_info(config)

    # Initialize processor with configuration-driven approach
    session_id = f"basic-usage-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        print(f"🔧 Creating processor with session ID: {session_id}")
        print("   All components (JobStatusSaver, ResultSaver, SchemaCollector) created from configuration...")

        # Processor now creates all components from configuration automatically
        processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)
        print("✓ Processor initialized successfully with configuration-driven components")
        print()
    except Exception as e:
        print(f"✗ Error initializing processor: {e}")
        print("  Make sure all configuration paths are valid and accessible")
        return

    try:
        print("🚀 Processing metadata through pipeline...")
        print("   This may take a moment for AI-powered predictions...")
        print()

        # Process metadata through complete pipeline
        # Note: Using example schema IDs - update these to match your actual schemas
        results = await processor.process(
            metadata_df=metadata_df, program_id="example-program-uuid", core_id="example-core-uuid"
        )

        # Display results
        print("=== 📊 Processing Results ===")
        print(f"✓ Total rows processed: {results.summary.total_rows}")
        print(f"  Total errors found: {results.summary.total_errors}")

        if results.summary.error_types:
            print("  Error breakdown:")
            for error_type, count in results.summary.error_types.items():
                print(f"    - {error_type}: {count}")
        print()

        if results.validation_results:
            print("=== 🔍 Validation Errors (first 10) ===")
            for i, error in enumerate(results.validation_results[:10]):
                print(f"{i+1}. Row {error.row}, Column '{error.column}': {error.error_type}")
                print(f"   Current value: '{error.current_value}'")
                if error.recommended_value:
                    print(f"   🤖 AI Recommendation: '{error.recommended_value}'")
                if error.valid_options:
                    print(f"   Valid options: {error.valid_options[:5]}{'...' if len(error.valid_options) > 5 else ''}")
                print()

            if len(results.validation_results) > 10:
                print(f"   ... and {len(results.validation_results) - 10} more errors")
                print()

        # Get processing state information
        state = processor.get_current_state()
        if state:
            duration = state.get_processing_duration()
            print(f"⏱️  Processing completed in {duration:.2f} seconds")
            print(f"📋 Job ID: {state.job_id}")
            print(f"🔄 Final stage: {state.current_stage}")
            print()

        # Show where data was saved
        print("💾 Data Storage:")
        if config.job_status_saver_type == "local":
            storage_dir = config.job_status_storage_dir or "./job_status"
            print(f"  - Job status: {storage_dir}/{state.job_id if state else session_id}.json")
        else:
            print(f"  - Job status: DynamoDB table '{config.job_status_table_name}'")

        if config.result_saver_type == "local":
            results_dir = config.results_local_dir or "./validation-results"
            print(f"  - Validation results: {results_dir}/{state.job_id if state else session_id}/v1/results.json")
            print("    💡 Tip: Results are saved with version tracking for easy retrieval")
        else:
            print(f"  - Validation results: S3 bucket '{config.results_s3_bucket}'")

        # Demonstrate result retrieval
        if state and config.result_saver_type == "local":
            print("\n🔍 Result Retrieval Demo:")
            try:
                # Access the result saver from the processor
                result_saver = processor.data_saver.result_saver

                # List all results for this job
                all_results = await result_saver.list_results(state.job_id)
                print(f"  - Found {len(all_results)} result versions for job {state.job_id}")

                if all_results:
                    # Retrieve the latest results
                    latest_result = all_results[0]  # Results are typically ordered by version
                    retrieved_results = await result_saver.get_results(latest_result)
                    if retrieved_results:
                        print(f"  - Successfully retrieved results: {retrieved_results.summary.total_errors} errors")
                        print(f"  - Storage location: {latest_result.location}")

            except Exception as e:
                print(f"  - Result retrieval demo failed: {e}")

        print("✅ Processing completed successfully!")

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check that schema_directory in config-basic.yaml points to valid schema files")
        print("2. Ensure you have proper permissions to write to job_status and session directories")
        print("3. If using AI features, check your AWS credentials and region settings")

    finally:
        # Clean up resources
        try:
            await processor.cleanup()
            print("🧹 Resources cleaned up successfully")
        except Exception as e:
            print(f"⚠️  Warning: Error during cleanup: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 MetadataHarmonizationProcessor - Basic Usage Example")
    print("=" * 70)
    print()
    print("SWITCHING TO PRODUCTION MODE:")
    print("To use this processor with AWS services in production:")
    print("1. Use config-production.yaml as a template")
    print("2. Update DynamoDB table name and S3 bucket")
    print("3. Configure AWS credentials (AWS CLI, IAM roles, etc.)")
    print("4. Update schema_directory path for your environment")
    print("5. Configure Redis endpoint if using caching")
    print()
    print("CURRENT MODE: Local Development (no AWS dependencies)")
    print("=" * 70)
    print()

    asyncio.run(main())
