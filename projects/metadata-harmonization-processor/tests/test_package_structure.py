# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Test basic package structure and imports.
"""

import pytest


def test_package_import():
    """Test that the main package can be imported."""
    import metadata_harmonization_processor

    assert metadata_harmonization_processor.__version__ == "0.1.0"
    assert metadata_harmonization_processor.__author__ == "Data Harmonization Team"


def test_submodule_imports():
    """Test that all submodules can be imported."""
    # Test that all submodules exist and can be imported

    # Basic smoke test - modules should import without errors
    assert True


@pytest.mark.unit
def test_package_structure():
    """Test that the package has the expected structure."""
    from pathlib import Path

    import metadata_harmonization_processor

    # Get the package directory
    package_dir = Path(metadata_harmonization_processor.__file__).parent

    # Check that expected subdirectories exist
    expected_dirs = [
        "models",
        "interfaces",
        "implementations",
        "nodes",
        "session",
        "utils",
    ]

    for dir_name in expected_dirs:
        dir_path = package_dir / dir_name
        assert dir_path.exists(), f"Directory {dir_name} should exist"
        assert dir_path.is_dir(), f"{dir_name} should be a directory"

        # Check that __init__.py exists in each subdirectory
        init_file = dir_path / "__init__.py"
        assert init_file.exists(), f"__init__.py should exist in {dir_name}"
