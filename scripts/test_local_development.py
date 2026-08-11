#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Test script for local development workflow.
This script tests Makefile commands, local API startup, environment variable generation,
and deployment verification with the updated configuration.
"""

import sys
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# Add project root to path for imports
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class LocalDevelopmentTestResult:
    """Container for test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors: List[str] = []
        self.warnings_list: List[str] = []

    def add_pass(self, message: str):
        """Add a passing test."""
        print(f"\t✓ PASS: {message}")
        self.passed += 1

    def add_fail(self, message: str):
        """Add a failing test."""
        print(f"\t✗ FAIL: {message}")
        self.failed += 1
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add a warning."""
        print(f"\t⚠ WARNING: {message}")
        self.warnings += 1
        self.warnings_list.append(message)

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed + self.warnings
        print(f"\n{'='*60}")
        print("LOCAL DEVELOPMENT WORKFLOW TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Warnings: {self.warnings}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings_list:
            print("\nWarnings:")
            for warning in self.warnings_list:
                print(f"  - {warning}")

        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if self.failed == 0:
            print("🎉 All critical tests passed!")
            return True
        else:
            print("❌ Some tests failed. Please review the errors above.")
            return False


class LocalDevelopmentTester:
    """Test local development workflow."""

    def __init__(self, config: Dict):
        self.config = config
        self.result = LocalDevelopmentTestResult()
        self.project_root = PROJECT_ROOT

    def run_command(self, command: str, cwd: Optional[Path] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return success, stdout, stderr."""
        try:
            if cwd is None:
                cwd = self.project_root

            # nosec B602 - shell=True is safe here: this is a local developer helper that is
            # never deployed, and every one of the six call sites passes a hardcoded literal
            # ("make help", "bash scripts/generate_dotenv.sh ...", etc). No caller-supplied or
            # user-supplied data reaches `command`. Keep it that way -- if this ever needs to
            # interpolate a variable, drop shell=True and pass an argument list instead.
            result = subprocess.run(  # nosec B602
                command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
            )

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def test_makefile_commands(self) -> None:
        """Test Makefile commands with updated package references."""
        print("Testing Makefile commands...")

        # Test help command
        success, stdout, stderr = self.run_command("make help")
        if success and "metadata-harmonization" in stdout.lower():
            self.result.add_pass("Makefile help command works and shows updated package references")
        else:
            self.result.add_fail("Makefile help command failed or doesn't show updated references")

        # Test loadEnvironmentVariables
        success, stdout, stderr = self.run_command("make loadEnvironmentVariables")
        if success:
            self.result.add_pass("Makefile loadEnvironmentVariables command works")
        else:
            self.result.add_warning(f"Makefile loadEnvironmentVariables failed: {stderr}")

        # Test installPythonRequirements
        success, stdout, stderr = self.run_command("make installPythonRequirements", timeout=120)
        if success:
            self.result.add_pass("Makefile installPythonRequirements command works")
        else:
            self.result.add_warning(f"Makefile installPythonRequirements failed: {stderr}")

        # Test installTypeScriptRequirements
        success, stdout, stderr = self.run_command("make installTypeScriptRequirements", timeout=120)
        if success:
            self.result.add_pass("Makefile installTypeScriptRequirements command works")
        else:
            self.result.add_warning(f"Makefile installTypeScriptRequirements failed: {stderr}")

        # Check that Makefile uses metadata harmonization references
        makefile_path = self.project_root / "Makefile"
        if makefile_path.exists():
            makefile_content = makefile_path.read_text()

            old_references = ["legacy-agent-api", "legacy-agent", "legacy-classifier", "LEGACY_AGENT_CONFIGS_DIR"]
            found_old_refs = [ref for ref in old_references if ref in makefile_content]

            if not found_old_refs:
                self.result.add_pass("Makefile has no legacy references")
            else:
                self.result.add_fail(f"Makefile still contains legacy references: {found_old_refs}")

            # Check for new metadata references
            new_references = ["metadata-harmonization-api", "metadata-harmonization", "metadata-validation"]
            found_new_refs = [ref for ref in new_references if ref in makefile_content]

            if len(found_new_refs) >= 2:  # At least 2 of the 3 references should be present
                self.result.add_pass("Makefile contains updated metadata harmonization references")
            else:
                self.result.add_warning("Makefile may be missing some updated references")

    def test_environment_variable_generation(self) -> None:
        """Test environment variable generation script."""
        print("\nTesting environment variable generation...")

        # Check if script exists
        env_script = self.project_root / "scripts" / "generate_dotenv.sh"
        if not env_script.exists():
            self.result.add_fail("Environment variable generation script not found")
            return

        # Check script content for updated variables
        script_content = env_script.read_text()

        # Check that old database variables are removed
        old_db_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD_SECRET_ARN"]
        found_old_vars = [var for var in old_db_vars if var in script_content]

        if not found_old_vars:
            self.result.add_pass("Environment generation script has no old database variables")
        else:
            self.result.add_fail(
                f"Environment generation script still contains old database variables: {found_old_vars}"
            )

        # Check for new metadata variables
        new_vars = [
            "METADATA_SCHEMAS_TABLE",
            "METADATA_UPLOAD_JOB_TABLE",
            "VALIDATION_RESULTS_BUCKET",
            "SCHEMA_STORAGE_BUCKET",
        ]
        found_new_vars = [var for var in new_vars if var in script_content]

        if len(found_new_vars) >= 3:  # At least 3 of the 4 variables should be present
            self.result.add_pass("Environment generation script contains new metadata variables")
        else:
            self.result.add_warning(
                f"Environment generation script may be missing some new variables. Found: {found_new_vars}"
            )

        # Try to run the script (it may fail due to missing AWS resources, but should not error on syntax)
        success, stdout, stderr = self.run_command(
            "bash scripts/generate_dotenv.sh test-stack us-east-1 default INFO", timeout=10
        )
        if "syntax error" not in stderr.lower() and "command not found" not in stderr.lower():
            self.result.add_pass("Environment generation script has no syntax errors")
        else:
            self.result.add_fail(f"Environment generation script has syntax errors: {stderr}")

    def test_deployment_verification_script(self) -> None:
        """Test deployment verification script with new infrastructure."""
        print("\nTesting deployment verification script...")

        # Check if script exists
        verify_script = self.project_root / "scripts" / "verify_deployment.py"
        if not verify_script.exists():
            self.result.add_fail("Deployment verification script not found")
            return

        # Check script content for updated functionality
        script_content = verify_script.read_text()

        # Check that old database checks are removed
        old_db_checks = ["postgresql", "psycopg", "database connection", "DB_HOST"]
        found_old_checks = [check for check in old_db_checks if check.lower() in script_content.lower()]

        if len(found_old_checks) <= 1:  # Some might be in comments or variable names
            self.result.add_pass("Deployment verification script has minimal old database references")
        else:
            self.result.add_warning(
                f"Deployment verification script may still have old database checks: {found_old_checks}"
            )

        # Check for new infrastructure checks
        new_checks = ["dynamodb", "s3", "metadata", "validation"]
        found_new_checks = [check for check in new_checks if check.lower() in script_content.lower()]

        if len(found_new_checks) >= 3:
            self.result.add_pass("Deployment verification script contains new infrastructure checks")
        else:
            self.result.add_warning(
                f"Deployment verification script may be missing some new checks. Found: {found_new_checks}"
            )

        # Try to run the script (it may fail due to missing AWS resources, but should not error on imports)
        success, stdout, stderr = self.run_command("python3 scripts/verify_deployment.py", timeout=10)
        if "ModuleNotFoundError" not in stderr and "ImportError" not in stderr:
            self.result.add_pass("Deployment verification script has no import errors")
        else:
            self.result.add_warning(f"Deployment verification script has import issues: {stderr}")

    def test_api_configuration(self) -> None:
        """Test API configuration and structure."""
        print("\nTesting API configuration...")

        # Check API main file
        api_main = self.project_root / "projects" / "api" / "src" / "metadata_harmonization_api" / "api" / "main.py"
        if api_main.exists():
            self.result.add_pass("API main file exists at correct path")

            main_content = api_main.read_text()

            # Check for legacy references
            old_refs = ["legacy_agent", "legacy-agent", "old_classification"]
            found_old_refs = [ref for ref in old_refs if ref in main_content]

            if not found_old_refs:
                self.result.add_pass("API main file has no legacy references")
            else:
                self.result.add_fail(f"API main file still contains legacy references: {found_old_refs}")

            # Check for new metadata references
            new_refs = ["metadata_harmonization_api", "metadata", "validation"]
            found_new_refs = [ref for ref in new_refs if ref in main_content]

            if len(found_new_refs) >= 2:
                self.result.add_pass("API main file contains new metadata references")
            else:
                self.result.add_warning("API main file may be missing some new references")
        else:
            self.result.add_fail("API main file not found at expected path")

        # Check router configuration
        api_router = self.project_root / "projects" / "api" / "src" / "metadata_harmonization_api" / "api" / "router.py"
        if api_router.exists():
            router_content = api_router.read_text()

            # Check for health endpoints
            if "/api/health" in router_content and "/api/v1" in router_content:
                self.result.add_pass("API router has correct health endpoint paths")
            else:
                self.result.add_warning("API router may have incorrect endpoint paths")

            # Check for metadata endpoints
            if "metadata" in router_content.lower() and "validation" in router_content.lower():
                self.result.add_pass("API router includes metadata validation endpoints")
            else:
                self.result.add_warning("API router may be missing metadata validation endpoints")
        else:
            self.result.add_fail("API router file not found")

    def test_local_api_startup(self) -> None:
        """Test local API startup with new environment variables."""
        print("\nTesting local API startup...")

        # Check entrypoint script
        entrypoint_script = self.project_root / "projects" / "infra" / "lib" / "api" / "entrypoint.sh"
        if entrypoint_script.exists():
            script_content = entrypoint_script.read_text()

            # Check for correct module path
            if "metadata_harmonization_api.api.main:app" in script_content:
                self.result.add_pass("Entrypoint script uses correct module path")
            else:
                self.result.add_fail("Entrypoint script has incorrect module path")

            # Check that old database initialization is removed
            if "database" not in script_content.lower() or "db" not in script_content.lower():
                self.result.add_pass("Entrypoint script has no database initialization")
            else:
                self.result.add_warning("Entrypoint script may still have database references")
        else:
            self.result.add_fail("Entrypoint script not found")

        # Test if we can import the API module
        try:
            sys.path.insert(0, str(self.project_root / "projects" / "api" / "src"))
            import metadata_harmonization_api.api.main  # noqa: F401

            self.result.add_pass("API module can be imported successfully")
        except ImportError as e:
            self.result.add_warning(f"API module import failed: {e}")
        except Exception as e:
            self.result.add_warning(f"API module import error: {e}")

    def test_api_endpoints_locally(self) -> None:
        """Test API endpoints if API is running locally."""
        print("\nTesting API endpoints (if running locally)...")

        # Test different possible local URLs
        base_urls = ["http://localhost:8080", "http://127.0.0.1:8080"]

        api_responding = False
        working_base_url = None

        for base_url in base_urls:
            try:
                response = requests.get(f"{base_url}/api/health", timeout=5)
                if response.status_code == 200:
                    api_responding = True
                    working_base_url = base_url
                    break
            except requests.exceptions.RequestException:
                continue

        if not api_responding:
            self.result.add_warning("API is not running locally - skipping endpoint tests")
            return

        self.result.add_pass(f"API is responding at {working_base_url}")

        # Test health endpoints
        endpoints_to_test = [
            ("/api/health", "Basic health endpoint"),
            ("/api/v1/health", "V1 health endpoint"),
            ("/api/v1/metadata/schema", "Metadata schema endpoint (may require auth)"),
        ]

        for endpoint, description in endpoints_to_test:
            try:
                response = requests.get(f"{working_base_url}{endpoint}", timeout=10)

                if response.status_code == 200:
                    self.result.add_pass(f"{description} returned 200 OK")

                    # Try to parse JSON
                    try:
                        json_data = response.json()
                        if isinstance(json_data, dict) and len(json_data) > 0:
                            self.result.add_pass(f"{description} returned valid JSON")
                    except ValueError:
                        self.result.add_warning(f"{description} did not return valid JSON")

                elif response.status_code in [401, 403]:
                    self.result.add_pass(f"{description} returned {response.status_code} (auth required - expected)")
                elif response.status_code == 404:
                    self.result.add_warning(f"{description} returned 404 - endpoint may not exist")
                else:
                    self.result.add_warning(f"{description} returned unexpected status {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.result.add_warning(f"{description} request failed: {e}")

    def test_configuration_files(self) -> None:
        """Test configuration files are updated correctly."""
        print("\nTesting configuration files...")

        # Test config.yaml.example
        config_example = self.project_root / "config.yaml.example"
        if config_example.exists():
            config_content = config_example.read_text()

            # Check for updated app name
            if "metadata-harmonization-app" in config_content:
                self.result.add_pass("Config example has updated app name")
            else:
                self.result.add_fail("Config example missing updated app name")

            # Check for metadata config section
            if "metadataConfig:" in config_content:
                self.result.add_pass("Config example has metadata configuration section")
            else:
                self.result.add_fail("Config example missing metadata configuration section")

            # Check that old RDS config is removed
            if "rdsConfig:" not in config_content and "database" not in config_content.lower():
                self.result.add_pass("Config example has no old database configuration")
            else:
                self.result.add_warning("Config example may still have old database configuration")
        else:
            self.result.add_fail("Config example file not found")

        # Test actual config.yaml if it exists
        config_file = self.project_root / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config_data = yaml.safe_load(f)

                # Check app name
                if config_data.get("appName") == "metadata-harmonization-app":
                    self.result.add_pass("Config file has correct app name")
                else:
                    self.result.add_warning("Config file may have incorrect app name")

                # Check for environment configuration
                env = config_data.get("env")
                if env and env in config_data:
                    env_config = config_data[env]

                    # Check for metadata config
                    if "metadataConfig" in env_config:
                        self.result.add_pass("Config file has metadata configuration")
                    else:
                        self.result.add_warning("Config file missing metadata configuration")

                    # Check that RDS config is not present
                    if "rdsConfig" not in env_config:
                        self.result.add_pass("Config file has no RDS configuration")
                    else:
                        self.result.add_fail("Config file still has RDS configuration")

            except yaml.YAMLError as e:
                self.result.add_fail(f"Config file has YAML syntax errors: {e}")
        else:
            self.result.add_warning("Config file not found (using example)")

    def run_all_tests(self) -> bool:
        """Run all local development tests."""
        print("Starting local development workflow tests")
        print(f"Project root: {self.project_root}")
        print(f"{'='*60}")

        # Run all tests
        self.test_configuration_files()
        self.test_makefile_commands()
        self.test_environment_variable_generation()
        self.test_deployment_verification_script()
        self.test_api_configuration()
        self.test_local_api_startup()
        self.test_api_endpoints_locally()

        # Print summary and return result
        return self.result.print_summary()


def main():
    """Main function to run local development tests."""
    # Read configuration
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config.yaml.example"

    if not config_path.exists():
        print("ERROR: No config.yaml or config.yaml.example found")
        sys.exit(1)

    with open(config_path, "r") as file:
        config_full = yaml.safe_load(file)

    # Parse config
    env = config_full.get("env", "dev")
    config_env = config_full.get(env, {})

    # Run tests
    tester = LocalDevelopmentTester(config_env)
    success = tester.run_all_tests()

    if success:
        print("\n🎉 All local development workflow tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some local development workflow tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
