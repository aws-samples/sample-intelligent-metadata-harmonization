# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Tests for Makefile environment setup and configuration."""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest


class TestMakefileEnvironmentSetup:
    """Test cases for Makefile environment variable setup."""

    def test_makefile_local_environment_variables(self):
        """Test that Makefile sets correct environment variables for local development."""
        # Expected environment variables for local mode
        expected_local_env = {
            "PROCESSOR_ENVIRONMENT": "local",
            "API_ENABLE_AUTH": "false",
            "PROCESSOR_JOB_STATUS_SAVER_TYPE": "local",
            "PROCESSOR_RESULT_SAVER_TYPE": "local",
            "PROCESSOR_SESSION_TYPE": "file",
            "PROCESSOR_LOCAL_DEVELOPMENT_MODE": "true",
            "PROCESSOR_ENABLE_REDIS_CACHE": "false",
            "PROCESSOR_ENABLE_MEMORY_CACHE": "true",
        }

        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check that run-local target contains all expected environment variables
        run_local_section = self._extract_makefile_target(makefile_content, "run-local")

        for env_var, expected_value in expected_local_env.items():
            env_line = f"export {env_var}={expected_value}"
            assert (
                env_line in run_local_section
            ), f"Missing or incorrect environment variable: {env_var}={expected_value}"

    def test_makefile_cloud_environment_variables(self):
        """Test that Makefile sets correct environment variables for cloud development."""
        # Expected environment variables for cloud mode
        expected_cloud_env = {
            "PROCESSOR_ENVIRONMENT": "cloud",
            "API_ENABLE_AUTH": "true",
            "PROCESSOR_JOB_STATUS_SAVER_TYPE": "dynamodb",
            "PROCESSOR_JOB_STATUS_TABLE_NAME": "metadata-upload-jobs",
            "PROCESSOR_RESULT_SAVER_TYPE": "s3",
            "PROCESSOR_RESULTS_S3_BUCKET": "metadata-validation-results",
            "PROCESSOR_RESULTS_S3_PREFIX": "results/",
            "PROCESSOR_SESSION_TYPE": "s3",
            "PROCESSOR_S3_BUCKET": "metadata-processor-sessions",
            "PROCESSOR_S3_PREFIX": "sessions/",
            "PROCESSOR_LOCAL_DEVELOPMENT_MODE": "false",
            "PROCESSOR_ENABLE_REDIS_CACHE": "true",
            "PROCESSOR_ENABLE_MEMORY_CACHE": "false",
        }

        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check that run-cloud target contains all expected environment variables
        run_cloud_section = self._extract_makefile_target(makefile_content, "run-cloud")

        for env_var, expected_value in expected_cloud_env.items():
            env_line = f"export {env_var}={expected_value}"
            assert (
                env_line in run_cloud_section
            ), f"Missing or incorrect environment variable: {env_var}={expected_value}"

    def test_makefile_production_environment_variables(self):
        """Test that Makefile sets correct environment variables for production."""
        # Expected environment variables for production mode
        expected_prod_env = {
            "PROCESSOR_ENVIRONMENT": "cloud",
            "API_ENABLE_AUTH": "true",
            "PROCESSOR_JOB_STATUS_SAVER_TYPE": "dynamodb",
            "PROCESSOR_RESULT_SAVER_TYPE": "s3",
            "PROCESSOR_SESSION_TYPE": "s3",
            "PROCESSOR_LOCAL_DEVELOPMENT_MODE": "false",
            "PROCESSOR_ENABLE_REDIS_CACHE": "true",
        }

        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check that run-prod target contains all expected environment variables
        run_prod_section = self._extract_makefile_target(makefile_content, "run-prod")

        for env_var, expected_value in expected_prod_env.items():
            env_line = f"export {env_var}={expected_value}"
            assert (
                env_line in run_prod_section
            ), f"Missing or incorrect environment variable: {env_var}={expected_value}"

    def test_makefile_targets_exist(self):
        """Test that all required Makefile targets exist."""
        required_targets = [
            "run-local",
            "run-cloud",
            "run-prod",
            "show-config",
            "show-config-cloud",
            "dev-setup",
            "dev-clean",
        ]

        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        for target in required_targets:
            target_line = f"{target}:"
            assert target_line in makefile_content, f"Missing Makefile target: {target}"

    def test_makefile_uvicorn_commands(self):
        """Test that Makefile targets use correct uvicorn commands."""
        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check run-local uses reload and correct host/port
        run_local_section = self._extract_makefile_target(makefile_content, "run-local")
        assert (
            "uvicorn metadata_harmonization_api.api.main:app --reload --host 0.0.0.0 --port 8080" in run_local_section
        )

        # Check run-cloud uses reload and correct host/port
        run_cloud_section = self._extract_makefile_target(makefile_content, "run-cloud")
        assert (
            "uvicorn metadata_harmonization_api.api.main:app --reload --host 0.0.0.0 --port 8080" in run_cloud_section
        )

        # Check run-prod uses production settings (no reload, multiple workers)
        run_prod_section = self._extract_makefile_target(makefile_content, "run-prod")
        assert (
            "uvicorn metadata_harmonization_api.api.main:app --host 0.0.0.0 --port 8080 --workers 4" in run_prod_section
        )
        assert "--reload" not in run_prod_section

    def test_makefile_help_target(self):
        """Test that help target exists and shows available commands."""
        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check help target exists
        assert "help:" in makefile_content

        # Check help target has proper documentation comment on the target line
        assert "help:" in makefile_content
        assert "## Show this help message" in makefile_content

        # Check help body uses grep to extract help text
        help_section = self._extract_makefile_target(makefile_content, "help")
        assert "grep -E" in help_section

    def test_makefile_phony_declaration(self):
        """Test that Makefile declares targets as PHONY."""
        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check .PHONY declaration exists
        assert ".PHONY:" in makefile_content

        # Check that important targets are declared as PHONY
        phony_targets = ["help", "test", "run-local", "run-cloud", "run-prod", "clean", "lint", "format", "install"]

        phony_line = None
        for line in makefile_content.split("\n"):
            if line.startswith(".PHONY:"):
                phony_line = line
                break

        assert phony_line is not None, "No .PHONY declaration found"

        for target in phony_targets:
            assert target in phony_line, f"Target {target} not declared as PHONY"

    def test_makefile_development_setup_targets(self):
        """Test that development setup targets create necessary directories."""
        # Read Makefile content
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        with open(makefile_path, "r") as f:
            makefile_content = f.read()

        # Check dev-setup target
        dev_setup_section = self._extract_makefile_target(makefile_content, "dev-setup")

        # Should create local directories
        assert "mkdir -p job_status" in dev_setup_section
        assert "mkdir -p validation-results" in dev_setup_section
        assert "mkdir -p sessions" in dev_setup_section

        # Should run install
        assert "make install" in dev_setup_section

        # Check dev-clean target
        dev_clean_section = self._extract_makefile_target(makefile_content, "dev-clean")

        # Should remove local directories
        assert "rm -rf job_status/" in dev_clean_section
        assert "rm -rf validation-results/" in dev_clean_section
        assert "rm -rf sessions/" in dev_clean_section

        # Should run clean
        assert "make clean" in dev_clean_section

    def _extract_makefile_target(self, makefile_content: str, target_name: str) -> str:
        """Extract the content of a specific Makefile target."""
        lines = makefile_content.split("\n")
        target_start = None
        target_content = []

        # Find the target
        for i, line in enumerate(lines):
            if line.startswith(f"{target_name}:"):
                target_start = i
                break

        if target_start is None:
            return ""

        # Extract target content until next target or end of file
        for i in range(target_start + 1, len(lines)):
            line = lines[i]

            # Stop at next target (line starting with word followed by colon, not indented)
            if (
                line
                and not line.startswith("\t")
                and not line.startswith(" ")
                and ":" in line
                and not line.startswith("#")
            ):
                break

            target_content.append(line)

        return "\n".join(target_content)


class TestMakefileEnvironmentIntegration:
    """Integration tests for Makefile environment setup."""

    @pytest.mark.slow
    def test_makefile_show_config_targets(self):
        """Test that show-config targets work correctly."""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"

        # Test show-config target
        try:
            result = subprocess.run(
                ["make", "-f", str(makefile_path), "show-config"], capture_output=True, text=True, timeout=10
            )

            # Should succeed
            assert result.returncode == 0

            # Should show local configuration
            output = result.stdout
            assert "PROCESSOR_ENVIRONMENT=local" in output
            assert "API_ENABLE_AUTH=false" in output
            assert "PROCESSOR_JOB_STATUS_SAVER_TYPE=local" in output

        except subprocess.TimeoutExpired:
            pytest.skip("Makefile execution timed out")
        except FileNotFoundError:
            pytest.skip("make command not available")

    @pytest.mark.slow
    def test_makefile_show_config_cloud_target(self):
        """Test that show-config-cloud target works correctly."""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"

        # Test show-config-cloud target
        try:
            result = subprocess.run(
                ["make", "-f", str(makefile_path), "show-config-cloud"], capture_output=True, text=True, timeout=10
            )

            # Should succeed
            assert result.returncode == 0

            # Should show cloud configuration
            output = result.stdout
            assert "PROCESSOR_ENVIRONMENT=cloud" in output
            assert "API_ENABLE_AUTH=true" in output
            assert "PROCESSOR_JOB_STATUS_SAVER_TYPE=dynamodb" in output

        except subprocess.TimeoutExpired:
            pytest.skip("Makefile execution timed out")
        except FileNotFoundError:
            pytest.skip("make command not available")

    @pytest.mark.slow
    def test_makefile_help_target_execution(self):
        """Test that help target executes correctly."""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"

        try:
            result = subprocess.run(
                ["make", "-f", str(makefile_path), "help"], capture_output=True, text=True, timeout=10
            )

            # Should succeed
            assert result.returncode == 0

            # Should show available commands
            output = result.stdout
            assert "Available commands:" in output
            assert "run-local" in output
            assert "run-cloud" in output
            assert "run-prod" in output

        except subprocess.TimeoutExpired:
            pytest.skip("Makefile execution timed out")
        except FileNotFoundError:
            pytest.skip("make command not available")


class TestMakefileConfigurationConsistency:
    """Test consistency between Makefile and configuration system."""

    def test_makefile_environment_variables_match_config_system(self):
        """Test that Makefile environment variables match what the config system expects."""
        from metadata_harmonization_api.services.processor_manager import detect_environment_overrides

        # Test local environment detection
        with patch.dict(
            os.environ,
            {
                "PROCESSOR_ENVIRONMENT": "local",
                "API_ENABLE_AUTH": "false",
                "PROCESSOR_JOB_STATUS_SAVER_TYPE": "local",
                "PROCESSOR_RESULT_SAVER_TYPE": "local",
                "PROCESSOR_SESSION_TYPE": "file",
                "PROCESSOR_LOCAL_DEVELOPMENT_MODE": "true",
                "PROCESSOR_ENABLE_REDIS_CACHE": "false",
                "PROCESSOR_ENABLE_MEMORY_CACHE": "true",
            },
            clear=False,
        ):
            overrides = detect_environment_overrides()

            # Should detect local environment correctly
            assert overrides["job_status_saver_type"] == "local"
            assert overrides["result_saver_type"] == "local"
            assert overrides["session_type"] == "file"
            assert overrides["local_development_mode"] is True
            assert overrides["enable_redis_cache"] is False
            assert overrides["enable_memory_cache"] is True

    def test_makefile_cloud_variables_match_config_system(self):
        """Test that Makefile cloud environment variables match config system expectations."""
        from metadata_harmonization_api.services.processor_manager import detect_environment_overrides

        # Test cloud environment detection with Makefile variables
        with patch.dict(
            os.environ,
            {
                "PROCESSOR_ENVIRONMENT": "cloud",
                "API_ENABLE_AUTH": "true",
                "PROCESSOR_JOB_STATUS_SAVER_TYPE": "dynamodb",
                "PROCESSOR_JOB_STATUS_TABLE_NAME": "metadata-upload-jobs",
                "PROCESSOR_RESULT_SAVER_TYPE": "s3",
                "PROCESSOR_RESULTS_S3_BUCKET": "metadata-validation-results",
                "PROCESSOR_RESULTS_S3_PREFIX": "results/",
                "PROCESSOR_SESSION_TYPE": "s3",
                "PROCESSOR_S3_BUCKET": "metadata-processor-sessions",
                "PROCESSOR_S3_PREFIX": "sessions/",
                "PROCESSOR_LOCAL_DEVELOPMENT_MODE": "false",
                "PROCESSOR_ENABLE_REDIS_CACHE": "true",
                "PROCESSOR_ENABLE_MEMORY_CACHE": "false",
            },
            clear=False,
        ):
            overrides = detect_environment_overrides()

            # Should detect cloud environment correctly
            assert overrides["job_status_saver_type"] == "dynamodb"
            assert overrides["result_saver_type"] == "s3"
            assert overrides["session_type"] == "s3"
            # enable_redis_cache is mapped via env var mappings in cloud mode
            assert overrides["enable_redis_cache"] is True
            # local_development_mode and enable_memory_cache are NOT in the
            # cloud env_mappings, so they are not included in overrides
            assert "local_development_mode" not in overrides
            assert "enable_memory_cache" not in overrides

            # Should include specific cloud settings from env var mappings
            assert overrides["job_status_table_name"] == "metadata-upload-jobs"
            assert overrides["results_s3_bucket"] == "metadata-validation-results"
            assert overrides["results_s3_prefix"] == "results/"
            assert overrides["s3_bucket"] == "metadata-processor-sessions"
            assert overrides["s3_prefix"] == "sessions/"

    def test_makefile_api_config_variables_match(self):
        """Test that Makefile API configuration variables are recognized by config system."""
        from metadata_harmonization_api.config import MetadataConfig

        # Test API configuration with Makefile variables
        with patch.dict(
            os.environ,
            {"API_ENABLE_AUTH": "true", "API_MAX_FILE_SIZE_MB": "100", "API_VALIDATION_TIMEOUT_SECONDS": "600"},
            clear=False,
        ):
            config = MetadataConfig()

            # Should pick up environment variables
            assert config.enable_auth is True
            assert config.max_file_size_mb == 100
            assert config.validation_timeout_seconds == 600
