# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Debug test for LLM resolution node.

Tests specific cases to debug LLM prompt and response behavior.
"""

import asyncio
from pathlib import Path

import pandas as pd
import pytest

from metadata_harmonization_processor.config import (
    LLMResolutionConfig,
    load_processor_settings,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.nodes.llm_resolution import LLMResolutionNode


@pytest.fixture
def llm_config():
    """Load LLM configuration for testing."""
    config_path = Path("config.yaml")
    if config_path.exists():
        full_config = load_processor_settings(config_path)
        return full_config.llm_resolution
    else:
        # Use defaults for testing
        return LLMResolutionConfig(
            model_id="amazon.nova-pro-v1:0",
            aws_region="us-east-1",
            min_confidence_level="low",
        )


@pytest.mark.asyncio
async def test_llm_design_description_case(llm_config):
    """
    Test LLM with the specific design_description case that's failing.

    Scenario:
    - Invalid value: "Unknown"
    - Valid options: ["Amplicon enrichment Nextera XT kit", "Amplicon enrichment DNA Prep kit"]
    - Context: Illumina HiSeq 3000, DNA Prep Library Kit
    - Expected: Should select "Amplicon enrichment DNA Prep kit"
    """

    print("\n" + "=" * 80)
    print("TESTING LLM RESOLUTION: design_description case")
    print("=" * 80)

    # Create the exact error scenario
    error = ValidationErrorDetail(
        row=1,
        column="design_description",
        current_value="Unknown",
        valid_options=[
            "Amplicon enrichment Nextera XT kit",
            "Amplicon enrichment DNA Prep kit",
        ],
        error_type=ValidationErrorType.INVALID_OPTION,
        error_message="Invalid option for design_description",
        schema_field_name="design_description",
    )

    # Create DataFrame with row context
    df = pd.DataFrame(
        [
            {
                "SampleId": "TEST001",
                "SequencingInstrument": "Illumina HiSeq 3000",
                "LibraryPreparationKit": "Illumina DNA Prep Library Kit",
                "Organism": "Cyclospora spp",
                "design_description": "Unknown",  # The error field
            }
        ]
    )

    # Create validation results
    validation_results = ValidationResults(
        validation_results=[error],
        summary=ValidationResultsSummary(
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            total_rows=1,
            columns_validated=1,
        ),
    )

    # Create combined results
    combined_results = CombinedResults(validation_results=validation_results)

    # Create processor state
    state = ProcessorState(
        job_id="test-llm-debug",
        program_id="test-program",
        core_id="test-core",
        aligned_df=df,
        combined_results=combined_results,
    )

    # Initialize LLM node
    node = LLMResolutionNode(llm_config)

    # Build prompt to see what LLM sees
    prompt = node._build_batch_prompt([error], state)

    print("\n" + "-" * 80)
    print("PROMPT SENT TO LLM:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    # Process with LLM
    result = await node.invoke_async(task="test", invocation_state={"processor_state": state})

    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(f"Status: {result.status}")
    print("Error after processing:")
    print(f"  - Recommended value: {error.recommended_value}")
    print(f"  - Correction node: {error.correction_node}")
    print(f"  - Confidence level: {error.confidence_level}")
    print(f"  - Confidence score: {error.confidence_score}")
    print("-" * 80)

    # Assertions
    assert result.status.name in [
        "COMPLETED",
        "SUCCESS",
    ], f"Node failed: {result.status}"

    # Check if recommendation was made
    if error.recommended_value:
        print(f"\n✅ LLM made recommendation: '{error.recommended_value}'")

        # Verify it's from valid options
        assert error.recommended_value in error.valid_options, (
            f"LLM recommended invalid value '{error.recommended_value}'. " f"Valid options: {error.valid_options}"
        )

        print("✅ Recommendation is from valid options")

        # Check if it selected the expected one (DNA Prep kit)
        if "DNA Prep kit" in error.recommended_value:
            print("✅ Selected the contextually appropriate option (DNA Prep kit)")
        else:
            print(f"⚠️  Selected different option: {error.recommended_value}")
            print("   (Expected 'Amplicon enrichment DNA Prep kit' based on context)")
    else:
        print("\n⚠️  LLM did not make recommendation")
        print("   Possible reasons:")
        print("   - Confidence below threshold")
        print("   - LLM call failed")
        print("   - Response validation failed")

    print("\n" + "=" * 80)


@pytest.mark.asyncio
async def test_llm_library_layout_case(llm_config):
    """
    Test LLM with the library_layout case.

    Scenario:
    - Invalid value: "Unknown"
    - Valid options: ["Single", "Paired"]
    - Context: Sequencing data
    - Should select one of the two options
    """

    print("\n" + "=" * 80)
    print("TESTING LLM RESOLUTION: library_layout case")
    print("=" * 80)

    # Create the error scenario
    error = ValidationErrorDetail(
        row=1,
        column="library_layout",
        current_value="Unknown",
        valid_options=["Single", "Paired"],
        error_type=ValidationErrorType.INVALID_OPTION,
        error_message="Invalid option for library_layout",
        schema_field_name="library_layout",
    )

    # Create DataFrame with row context
    df = pd.DataFrame(
        [
            {
                "SampleId": "TEST001",
                "SequencingInstrument": "Illumina HiSeq 3000",
                "LibraryPreparationKit": "Illumina DNA Prep Library Kit",
                "library_layout": "Unknown",  # The error field
            }
        ]
    )

    # Create validation results
    validation_results = ValidationResults(
        validation_results=[error],
        summary=ValidationResultsSummary(
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            total_rows=1,
            columns_validated=1,
        ),
    )

    # Create combined results
    combined_results = CombinedResults(validation_results=validation_results)

    # Create processor state
    state = ProcessorState(
        job_id="test-llm-debug-2",
        program_id="test-program",
        core_id="test-core",
        aligned_df=df,
        combined_results=combined_results,
    )

    # Initialize LLM node
    node = LLMResolutionNode(llm_config)

    # Build prompt to see what LLM sees
    prompt = node._build_batch_prompt([error], state)

    print("\n" + "-" * 80)
    print("PROMPT SENT TO LLM:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    # Process with LLM
    result = await node.invoke_async(task="test", invocation_state={"processor_state": state})

    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(f"Status: {result.status}")
    print("Error after processing:")
    print(f"  - Recommended value: {error.recommended_value}")
    print(f"  - Correction node: {error.correction_node}")
    print(f"  - Confidence level: {error.confidence_level}")
    print(f"  - Confidence score: {error.confidence_score}")
    print("-" * 80)

    # Assertions
    assert result.status.name in [
        "COMPLETED",
        "SUCCESS",
    ], f"Node failed: {result.status}"

    # Check if recommendation was made
    if error.recommended_value:
        print(f"\n✅ LLM made recommendation: '{error.recommended_value}'")

        # Verify it's from valid options
        assert error.recommended_value in error.valid_options, (
            f"LLM recommended invalid value '{error.recommended_value}'. " f"Valid options: {error.valid_options}"
        )

        print("✅ Recommendation is from valid options")
    else:
        print("\n⚠️  LLM did not make recommendation")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    """Run tests directly for debugging."""

    # Load config
    config_path = Path("config.yaml")
    if config_path.exists():
        full_config = load_processor_settings(config_path)
        debug_llm_config = full_config.llm_resolution
    else:
        debug_llm_config = LLMResolutionConfig(
            model_id="amazon.nova-pro-v1:0",
            aws_region="us-east-1",
            min_confidence_level="low",
        )

    # Run tests
    print("Running LLM Resolution Debug Tests...")
    asyncio.run(test_llm_design_description_case(debug_llm_config))
    asyncio.run(test_llm_library_layout_case(debug_llm_config))
