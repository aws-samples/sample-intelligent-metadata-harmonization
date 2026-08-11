# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Pytest configuration and fixtures for integration tests.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp(prefix="eval_test_"))
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_dataset_path():
    """Path to a sample dataset for testing."""
    return Path("data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40.csv")


@pytest.fixture
def sample_ground_truth_path():
    """Path to a sample ground truth file for testing."""
    return Path("data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40_mappings.json")


@pytest.fixture
def processor_config_path():
    """Path to processor configuration file."""
    return Path("projects/metadata-harmonization-processor/config.yaml")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Ensure required directories exist
    Path("evaluation_results").mkdir(exist_ok=True)

    yield

    # Cleanup after test if needed
    pass
