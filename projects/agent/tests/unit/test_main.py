# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for the agent CLI entry point."""

from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from metadata_agent import main as main_module


class TestInteractiveCommand:
    """Test the `interactive` CLI command."""

    def test_interactive_starts_the_interactive_session(self):
        """The interactive command must call run_interactive_agent, not a
        differently-named function, or the session silently fails."""
        with (
            patch.object(main_module, "_check_demo_prerequisites", return_value=True),
            patch(
                "metadata_agent.examples.interactive_agent.InteractiveAgent.run_interactive_session",
                new_callable=AsyncMock,
            ) as mock_run_session,
        ):
            runner = CliRunner()
            result = runner.invoke(main_module.cli, ["interactive"])

        assert "is not defined" not in result.output
        assert "Interactive agent session failed" not in result.output
        mock_run_session.assert_called_once()
