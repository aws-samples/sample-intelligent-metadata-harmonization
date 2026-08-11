# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Interactive CLI agent with comprehensive test data and real-time MCP tracing."""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.markdown import Markdown

from ..main import MetadataAgent
from ..config import AgentConfig

console = Console()
logger = logging.getLogger(__name__)


class InteractiveAgent:
    """Interactive CLI agent for continuous metadata harmonization operations with comprehensive test data support."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = MetadataAgent(config)
        self.test_data_path = Path(config.test_data_dir)
        self.session_history: List[Dict[str, str]] = []
        self.mcp_tracing_enabled = True
        self.test_data_cache: Dict[str, Dict[str, Any]] = {}
        self.correction_examples: Dict[str, Dict[str, Any]] = {}

    async def run_interactive_session(self):
        """Run the interactive agent session."""
        await self._display_welcome()

        try:
            # Initialize the agent
            await self.agent.initialize()

            # Main interaction loop
            await self._main_loop()

        except Exception as e:
            console.print(f"[red]Interactive session failed:[/red] {e}")
            logger.exception("Interactive session failed")
        finally:
            await self.agent.shutdown()

    async def _display_welcome(self):
        """Display welcome message and help information."""
        welcome_text = """
# 🤖 Interactive Metadata Harmonization Agent

Welcome to the comprehensive interactive agent! This tool provides:

- **🔍 Schema Discovery** - Explore available schemas and their requirements
- **✅ Data Validation** - Validate metadata using natural language queries
- **📊 Test Data Suite** - Access comprehensive test datasets (valid, invalid, edge cases)
- **🔧 Error Correction** - Learn from before/after correction examples
- **📈 Real-time Tracing** - See detailed MCP communication traces
- **🎯 Guided Workflows** - Step-by-step validation and correction processes

## Available Commands

- `help` - Show this comprehensive help message
- `examples` - Show categorized example queries with test data
- `test-data` - Browse and analyze available test data files
- `scenarios` - Run pre-configured validation and correction scenarios
- `corrections` - Explore error correction examples and workflows
- `compare` - Compare before/after correction data side-by-side
- `analyze` - Deep analysis of test data files and their characteristics
- `history` - Show your query history with success/failure tracking
- `trace` - Toggle detailed MCP tracing visibility
- `stats` - Show session statistics and performance metrics
- `clear` - Clear the console and start fresh
- `quit` - Exit the interactive session

## Test Data Categories

- **✅ Valid Data** - Files that pass all validation checks
- **❌ Invalid Data** - Files with common validation errors
- **⚠️ Edge Cases** - Boundary conditions and unusual scenarios
- **🔧 Corrections** - Before/after examples showing error fixes

## Getting Started

Try these example queries:
- "List all available schemas and their purposes"
- "Validate patient_data_basic.csv and show me the results"
- "What validation errors are in missing_required_fields.csv?"
- "Compare before_correction.csv and after_correction.csv"
- "Show me how to fix date format errors step by step"
- "Analyze the edge case files and explain what makes them challenging"
        """

        console.print(Panel(Markdown(welcome_text), title="🚀 Interactive Agent", border_style="blue", padding=(1, 2)))

    async def _main_loop(self):
        """Main interaction loop."""
        console.print("\n[bold green]Agent ready![/bold green] Type your queries or commands below.")
        console.print(
            "[dim]Tip: Start with 'examples' to see what you can do, or 'test-data' to explore sample files.[/dim]\n"
        )

        while True:
            try:
                query = Prompt.ask("[bold cyan]❯[/bold cyan]", default="").strip()

                if not query:
                    continue

                # Handle special commands
                if await self._handle_command(query):
                    continue

                # Execute natural language query
                await self._execute_query(query)

            except KeyboardInterrupt:
                if Confirm.ask("\n[yellow]Exit interactive session?[/yellow]"):
                    break
                console.print()
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                logger.exception("Query execution error")

    async def _handle_command(self, query: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        command = query.lower().strip()

        if command in ["quit", "exit", "q"]:
            return True

        elif command == "help":
            await self._display_welcome()
            return True

        elif command == "examples":
            self._show_example_queries()
            return True

        elif command == "test-data":
            self._show_test_data()
            return True

        elif command == "scenarios":
            await self._run_test_scenarios()
            return True

        elif command == "history":
            self._show_history()
            return True

        elif command == "trace":
            self._toggle_tracing()
            return True

        elif command == "corrections":
            await self._show_correction_examples()
            return True

        elif command == "compare":
            await self._run_comparison_tool()
            return True

        elif command == "analyze":
            await self._run_data_analysis()
            return True

        elif command == "stats":
            self._show_session_stats()
            return True

        elif command == "clear":
            console.clear()
            await self._display_welcome()
            return True

        return False

    def _show_example_queries(self):
        """Display example queries users can try."""
        examples = [
            {
                "category": "Schema Discovery & Exploration",
                "queries": [
                    "List all available schemas with their descriptions and use cases",
                    "What are the required vs optional fields for patient demographic data?",
                    "Show me the COVID surveillance schema details including field definitions",
                    "What date and time formats are accepted across all schemas?",
                    "Which schemas can be combined for validation and how?",
                    "What are the most complex validation rules in the schemas?",
                ],
            },
            {
                "category": "Validation Operations with Test Data",
                "queries": [
                    "Validate patient_data_basic.csv using the appropriate schemas",
                    "Check covid_surveillance.csv for validation errors and show results",
                    "Validate missing_required_fields.csv and explain what's wrong",
                    "Process large_dataset.csv and report on validation performance",
                    "Validate cyclospora_outbreak.csv and show me the validation workflow",
                    "Test patient_data_complete.csv against all applicable schemas",
                ],
            },
            {
                "category": "Error Analysis & Troubleshooting",
                "queries": [
                    "What specific validation errors are in wrong_data_types.csv?",
                    "Analyze invalid_date_formats.csv and show me how to fix the date errors",
                    "Compare before_correction.csv and after_correction.csv to show improvements",
                    "Examine malformed_csv.csv and explain why it fails validation",
                    "What makes invalid_enum_values.csv fail and how can I fix it?",
                    "Analyze out_of_range_values.csv and show me the constraint violations",
                ],
            },
            {
                "category": "Edge Cases & Boundary Testing",
                "queries": [
                    "Analyze empty_file.csv - how does the system handle empty data?",
                    "What happens when I validate headers_only.csv with no data rows?",
                    "Test special_characters.csv for character encoding and validation issues",
                    "How does the system handle the large_dataset.csv performance-wise?",
                    "Examine malformed_csv.csv for CSV parsing and structure issues",
                ],
            },
            {
                "category": "Correction Workflows & Learning",
                "queries": [
                    "Walk me through the complete correction workflow for missing_required_fields.csv",
                    "Show me step-by-step how invalid_date_formats_corrected.csv was fixed",
                    "Compare wrong_data_types.csv with its corrected version",
                    "What's the systematic approach to fixing validation errors?",
                    "How do I prevent the most common validation errors?",
                    "Show me the before/after for all correction examples",
                ],
            },
            {
                "category": "Advanced Analysis & Insights",
                "queries": [
                    "Analyze all invalid test files and categorize the error types",
                    "What patterns do you see across all the valid test data files?",
                    "Which validation rules are most commonly violated in our test data?",
                    "Compare the complexity of different schema validation requirements",
                    "What test data gaps exist in our current test suite?",
                    "Assess the overall quality and coverage of our test data collection",
                ],
            },
        ]

        console.print("\n[bold]Example Queries You Can Try:[/bold]")

        for category in examples:
            console.print(f"\n[bold blue]{category['category']}:[/bold blue]")
            for query in category["queries"]:
                console.print(f"  • [cyan]{query}[/cyan]")

        console.print("\n[dim]💡 Tip: You can reference any test data file by name in your queries![/dim]")

    def _show_test_data(self):
        """Display available test data files with descriptions."""
        if not self.test_data_path.exists():
            console.print("[red]Test data directory not found![/red]")
            return

        console.print("\n[bold]Available Test Data Files:[/bold]")

        categories = {
            "valid": ("✅ Valid Data", "green"),
            "invalid": ("❌ Invalid Data", "red"),
            "edge_cases": ("⚠️  Edge Cases", "yellow"),
            "corrections": ("🔧 Corrections", "blue"),
        }

        for category, (title, color) in categories.items():
            category_path = self.test_data_path / category
            if not category_path.exists():
                continue

            console.print(f"\n[bold {color}]{title}:[/bold {color}]")

            files = list(category_path.glob("*.csv"))
            if not files:
                console.print("  [dim]No files found[/dim]")
                continue

            for file in sorted(files):
                file_size = file.stat().st_size
                size_str = self._format_file_size(file_size)
                console.print(f"  • [cyan]{file.name}[/cyan] [dim]({size_str})[/dim]")

        # Show correction mapping if available
        correction_mapping = self.test_data_path / "corrections" / "correction_mapping.json"
        if correction_mapping.exists():
            console.print("\n[bold blue]📋 Additional Files:[/bold blue]")
            console.print("  • [cyan]correction_mapping.json[/cyan] [dim](correction examples)[/dim]")

        console.print("\n[dim]💡 Use these file names in your queries to validate or analyze specific datasets![/dim]")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    async def _run_test_scenarios(self):
        """Run pre-configured test scenarios."""
        scenarios = [
            {
                "name": "Basic Validation Success Path",
                "description": "Validate files that should pass all validation checks",
                "query": "Validate patient_data_basic.csv and covid_surveillance.csv using appropriate schemas and show successful validation results",
            },
            {
                "name": "Comprehensive Error Detection",
                "description": "Identify and categorize different types of validation errors",
                "query": "Validate missing_required_fields.csv, wrong_data_types.csv, and invalid_date_formats.csv. Categorize the different error types found.",
            },
            {
                "name": "Schema Discovery & Requirements",
                "description": "Comprehensive schema exploration and field requirements",
                "query": "List all available schemas, show their required fields, data types, and validation rules. Explain which schemas work together.",
            },
            {
                "name": "Complete Error Correction Workflow",
                "description": "End-to-end correction process with before/after analysis",
                "query": "Compare all correction pairs (before_correction.csv vs after_correction.csv, invalid_date_formats.csv vs invalid_date_formats_corrected.csv) and explain the correction process",
            },
            {
                "name": "Edge Case & Boundary Testing",
                "description": "Test system robustness with challenging edge cases",
                "query": "Analyze empty_file.csv, headers_only.csv, malformed_csv.csv, and special_characters.csv. Explain how the system handles each edge case.",
            },
            {
                "name": "Performance & Scale Testing",
                "description": "Test validation performance with large datasets",
                "query": "Validate large_dataset.csv and report on validation performance, processing time, and any scalability considerations",
            },
            {
                "name": "Enumeration & Categorical Validation",
                "description": "Test categorical field validation and enumerated values",
                "query": "Analyze invalid_enum_values.csv to understand categorical validation failures and show the correct enumerated values for each field",
            },
            {
                "name": "Numeric Range & Constraint Testing",
                "description": "Test numeric validation rules and range constraints",
                "query": "Examine out_of_range_values.csv to understand numeric constraint violations and show the valid ranges for each numeric field",
            },
            {
                "name": "Multi-Schema Validation Workflow",
                "description": "Test validation across different schema combinations",
                "query": "Validate cyclospora_outbreak.csv and patient_data_complete.csv using different schema combinations and compare the validation requirements",
            },
            {
                "name": "Complete Test Suite Analysis",
                "description": "Comprehensive analysis of the entire test data suite",
                "query": "Analyze the complete test data suite: categorize all files by validation status, identify error patterns, assess schema coverage, and recommend improvements",
            },
        ]

        console.print("\n[bold]Pre-configured Test Scenarios:[/bold]")

        for i, scenario in enumerate(scenarios, 1):
            console.print(f"\n[bold cyan]{i}. {scenario['name']}[/bold cyan]")
            console.print(f"   [dim]{scenario['description']}[/dim]")

        console.print()

        while True:
            try:
                choice = IntPrompt.ask("Select a scenario to run (1-6), or 0 to return", default=0, show_default=True)

                if choice == 0:
                    break

                if 1 <= choice <= len(scenarios):
                    scenario = scenarios[choice - 1]
                    console.print(f"\n[bold]Running: {scenario['name']}[/bold]")
                    await self._execute_query(scenario["query"])

                    if not Confirm.ask("\nRun another scenario?", default=True):
                        break
                else:
                    console.print("[red]Invalid choice. Please select 1-6 or 0.[/red]")

            except (ValueError, KeyboardInterrupt):
                break

    def _show_history(self):
        """Show query history."""
        if not self.session_history:
            console.print("[yellow]No queries in history yet.[/yellow]")
            return

        console.print("\n[bold]Query History:[/bold]")

        for i, entry in enumerate(self.session_history[-10:], 1):  # Show last 10
            console.print(f"\n[bold cyan]{i}.[/bold cyan] [dim]{entry['timestamp']}[/dim]")
            console.print(f"   [white]Query:[/white] {entry['query']}")
            if entry.get("success"):
                console.print("   [green]✓ Success[/green]")
            else:
                console.print(f"   [red]✗ Failed: {entry.get('error', 'Unknown error')}[/red]")

        if len(self.session_history) > 10:
            console.print(f"\n[dim]... and {len(self.session_history) - 10} more entries[/dim]")

    def _toggle_tracing(self):
        """Toggle MCP tracing visibility."""
        # This would toggle the tracer's verbosity
        console.print("[yellow]Tracing toggle not implemented yet.[/yellow]")
        console.print("[dim]MCP traces are currently always visible during query execution.[/dim]")

    async def _execute_query(self, query: str):
        """Execute a natural language query and handle the response with optional tracing."""
        from datetime import datetime

        # Add to history
        history_entry = {
            "query": query,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "success": False,
            "start_time": datetime.now(),
        }

        try:
            # Display query being executed
            query_panel = Panel(
                f"[bold]Executing:[/bold] {query}", border_style="cyan", title="🔍 Query", padding=(0, 1)
            )
            console.print(query_panel)

            # Show tracing status
            if self.mcp_tracing_enabled:
                console.print("[dim]📡 MCP tracing enabled - showing detailed communication[/dim]")
            else:
                console.print("[dim]📡 MCP tracing disabled - showing results only[/dim]")

            # Execute the query
            logger.info(f"🔍 Executing interactive query: {query}")
            await self.agent.execute_query(query)

            # Mark as successful and record timing
            history_entry["success"] = True
            history_entry["duration"] = (datetime.now() - history_entry["start_time"]).total_seconds()

            # Log successful completion
            logger.info(f"✅ Query completed successfully in {history_entry['duration']:.2f}s")

        except Exception as e:
            history_entry["error"] = str(e)
            history_entry["duration"] = (datetime.now() - history_entry["start_time"]).total_seconds()
            console.print(f"[red]Query execution failed:[/red] {e}")
            logger.exception("Query execution failed")

        finally:
            # Clean up timing info before storing
            del history_entry["start_time"]
            self.session_history.append(history_entry)

    async def _show_correction_examples(self):
        """Show error correction examples and workflows."""
        console.print("\n[bold]🔧 Error Correction Examples & Workflows[/bold]")

        corrections_path = self.test_data_path / "corrections"
        if not corrections_path.exists():
            console.print("[red]Corrections directory not found![/red]")
            return

        # Load correction mapping if available
        mapping_file = corrections_path / "correction_mapping.json"
        correction_mapping = {}

        if mapping_file.exists():
            try:
                with open(mapping_file, "r") as f:
                    correction_mapping = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load correction mapping: {e}")

        # Show available correction examples
        correction_files = list(corrections_path.glob("*corrected.csv"))

        if not correction_files:
            console.print("[yellow]No correction examples found.[/yellow]")
            return

        console.print("\n[bold blue]Available Correction Examples:[/bold blue]")

        for i, file in enumerate(correction_files, 1):
            base_name = file.name.replace("_corrected.csv", "")
            original_file = self.test_data_path / "invalid" / f"{base_name}.csv"

            console.print(f"\n[bold cyan]{i}. {base_name.replace('_', ' ').title()}[/bold cyan]")

            if original_file.exists():
                console.print(f"   [red]Before:[/red] {original_file.name}")
                console.print(f"   [green]After:[/green] {file.name}")

                # Show correction details from mapping if available
                if base_name in correction_mapping:
                    details = correction_mapping[base_name]
                    console.print(f"   [yellow]Errors Fixed:[/yellow] {details.get('errors_fixed', 'Unknown')}")
                    console.print(f"   [blue]Changes Made:[/blue] {details.get('changes_made', 'See file comparison')}")
            else:
                console.print("   [dim]Original file not found[/dim]")

        # Interactive correction exploration
        console.print()

        while True:
            try:
                choice = IntPrompt.ask(
                    "Select a correction example to explore (1-{}) or 0 to return".format(len(correction_files)),
                    default=0,
                    show_default=True,
                )

                if choice == 0:
                    break

                if 1 <= choice <= len(correction_files):
                    await self._explore_correction_example(correction_files[choice - 1], correction_mapping)

                    if not Confirm.ask("\nExplore another correction example?", default=True):
                        break
                else:
                    console.print(f"[red]Invalid choice. Please select 1-{len(correction_files)} or 0.[/red]")

            except (ValueError, KeyboardInterrupt):
                break

    async def _explore_correction_example(self, corrected_file: Path, mapping: Dict[str, Any]):
        """Explore a specific correction example in detail."""
        base_name = corrected_file.name.replace("_corrected.csv", "")
        original_file = self.test_data_path / "invalid" / f"{base_name}.csv"

        console.print(f"\n[bold]🔍 Exploring: {base_name.replace('_', ' ').title()}[/bold]")

        if not original_file.exists():
            console.print("[red]Original file not found for comparison.[/red]")
            return

        # Show file comparison
        console.print("\n[bold]📊 File Comparison:[/bold]")

        try:
            # Read both files
            with open(original_file, "r") as f:
                original_content = f.read()
            with open(corrected_file, "r") as f:
                corrected_content = f.read()

            # Display side-by-side comparison
            self.tracer.display_before_after(
                original_content[:1000] + "..." if len(original_content) > 1000 else original_content,
                corrected_content[:1000] + "..." if len(corrected_content) > 1000 else corrected_content,
                f"Correction Example: {base_name}",
            )

            # Show correction details
            if base_name in mapping:
                details = mapping[base_name]
                details_panel = Panel(
                    f"[bold]Error Type:[/bold] {details.get('error_type', 'Unknown')}\n"
                    f"[bold]Errors Fixed:[/bold] {details.get('errors_fixed', 'Unknown')}\n"
                    f"[bold]Changes Made:[/bold] {details.get('changes_made', 'See comparison above')}\n"
                    f"[bold]Validation Result:[/bold] {details.get('validation_result', 'Should pass validation')}",
                    title="🔧 Correction Details",
                    border_style="blue",
                )
                console.print(details_panel)

            # Offer to validate both files
            if Confirm.ask("\nValidate both files to see the difference?", default=True):
                await self._validate_correction_pair(original_file, corrected_file)

        except Exception as e:
            console.print(f"[red]Failed to read correction files:[/red] {e}")

    async def _validate_correction_pair(self, original_file: Path, corrected_file: Path):
        """Validate both original and corrected files to show the difference."""
        console.print("\n[bold]🔍 Validation Comparison:[/bold]")

        # Validate original file
        console.print("\n[red]Validating Original (Invalid) File:[/red]")
        original_query = f"Validate the {original_file.name} file and show me all validation errors"
        await self._execute_query(original_query)

        # Validate corrected file
        console.print("\n[green]Validating Corrected File:[/green]")
        corrected_query = f"Validate the {corrected_file.name} file and confirm it passes validation"
        await self._execute_query(corrected_query)

    async def _run_comparison_tool(self):
        """Run interactive comparison tool for test data files."""
        console.print("\n[bold]📊 Data Comparison Tool[/bold]")
        console.print("[dim]Compare any two test data files side by side[/dim]")

        # Get list of all CSV files
        all_files = []
        for category in ["valid", "invalid", "edge_cases", "corrections"]:
            category_path = self.test_data_path / category
            if category_path.exists():
                files = list(category_path.glob("*.csv"))
                for file in files:
                    all_files.append((category, file))

        if not all_files:
            console.print("[red]No CSV files found for comparison.[/red]")
            return

        # Display available files
        console.print("\n[bold]Available Files:[/bold]")
        for i, (category, file) in enumerate(all_files, 1):
            console.print(f"  {i:2d}. [{category}] {file.name}")

        console.print()

        try:
            # Get first file
            file1_idx = IntPrompt.ask(f"Select first file (1-{len(all_files)})", show_default=False) - 1

            if not (0 <= file1_idx < len(all_files)):
                console.print("[red]Invalid selection.[/red]")
                return

            # Get second file
            file2_idx = IntPrompt.ask(f"Select second file (1-{len(all_files)})", show_default=False) - 1

            if not (0 <= file2_idx < len(all_files)):
                console.print("[red]Invalid selection.[/red]")
                return

            # Compare the files
            file1 = all_files[file1_idx][1]
            file2 = all_files[file2_idx][1]

            await self._compare_files(file1, file2)

        except (ValueError, KeyboardInterrupt):
            console.print("[yellow]Comparison cancelled.[/yellow]")

    async def _compare_files(self, file1: Path, file2: Path):
        """Compare two files side by side."""
        console.print("\n[bold]📊 Comparing Files:[/bold]")
        console.print(f"[cyan]File 1:[/cyan] {file1.name}")
        console.print(f"[cyan]File 2:[/cyan] {file2.name}")

        try:
            # Read both files
            with open(file1, "r") as f:
                content1 = f.read()
            with open(file2, "r") as f:
                content2 = f.read()

            # Display comparison
            self.tracer.display_before_after(
                content1[:1000] + "..." if len(content1) > 1000 else content1,
                content2[:1000] + "..." if len(content2) > 1000 else content2,
                f"File Comparison: {file1.name} vs {file2.name}",
            )

            # Offer to validate both files
            if Confirm.ask("\nValidate both files to compare results?", default=True):
                console.print(f"\n[bold]Validating {file1.name}:[/bold]")
                await self._execute_query(f"Validate {file1.name} and show results")

                console.print(f"\n[bold]Validating {file2.name}:[/bold]")
                await self._execute_query(f"Validate {file2.name} and show results")

        except Exception as e:
            console.print(f"[red]Failed to compare files:[/red] {e}")

    async def _run_data_analysis(self):
        """Run deep analysis of test data files."""
        console.print("\n[bold]🔬 Test Data Analysis Tool[/bold]")
        console.print(
            "[dim]Analyze test data files to understand their characteristics and validation challenges[/dim]"
        )

        analysis_options = [
            {
                "name": "Analyze All Invalid Data",
                "description": "Examine all invalid test files to understand common error patterns",
                "query": "Analyze all the invalid test data files and summarize the types of validation errors they contain",
            },
            {
                "name": "Edge Case Analysis",
                "description": "Explore edge cases and boundary conditions in test data",
                "query": "Analyze the edge case test files and explain what makes each one challenging for validation",
            },
            {
                "name": "Valid Data Patterns",
                "description": "Examine valid test files to understand successful data patterns",
                "query": "Analyze the valid test data files and show me what makes them pass validation successfully",
            },
            {
                "name": "Data Quality Assessment",
                "description": "Overall assessment of test data quality and coverage",
                "query": "Assess the overall quality and coverage of our test data suite. What validation scenarios are well covered?",
            },
            {
                "name": "Schema Coverage Analysis",
                "description": "Analyze which schemas are covered by our test data",
                "query": "Which schemas are covered by our test data files? Are there any gaps in schema coverage?",
            },
        ]

        console.print("\n[bold]Analysis Options:[/bold]")
        for i, option in enumerate(analysis_options, 1):
            console.print(f"\n[bold cyan]{i}. {option['name']}[/bold cyan]")
            console.print(f"   [dim]{option['description']}[/dim]")

        console.print()

        while True:
            try:
                choice = IntPrompt.ask(
                    f"Select analysis to run (1-{len(analysis_options)}) or 0 to return", default=0, show_default=True
                )

                if choice == 0:
                    break

                if 1 <= choice <= len(analysis_options):
                    option = analysis_options[choice - 1]
                    console.print(f"\n[bold]Running: {option['name']}[/bold]")
                    await self._execute_query(option["query"])

                    if not Confirm.ask("\nRun another analysis?", default=True):
                        break
                else:
                    console.print(f"[red]Invalid choice. Please select 1-{len(analysis_options)} or 0.[/red]")

            except (ValueError, KeyboardInterrupt):
                break

    def _show_session_stats(self):
        """Show session statistics and performance metrics."""
        console.print("\n[bold]📈 Session Statistics[/bold]")

        if not self.session_history:
            console.print("[yellow]No queries executed yet.[/yellow]")
            return

        # Calculate statistics
        total_queries = len(self.session_history)
        successful_queries = sum(1 for entry in self.session_history if entry.get("success", False))
        failed_queries = total_queries - successful_queries
        success_rate = (successful_queries / total_queries) * 100 if total_queries > 0 else 0

        # Create statistics table
        stats_table = Table(show_header=True, header_style="bold blue")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("Total Queries", str(total_queries))
        stats_table.add_row("Successful", f"[green]{successful_queries}[/green]")
        stats_table.add_row("Failed", f"[red]{failed_queries}[/red]")
        stats_table.add_row("Success Rate", f"{success_rate:.1f}%")

        if self.session_history:
            first_query = self.session_history[0]["timestamp"]
            last_query = self.session_history[-1]["timestamp"]
            stats_table.add_row("Session Duration", f"{first_query} - {last_query}")

        console.print(stats_table)

        # Show recent query types
        if total_queries > 0:
            console.print("\n[bold]Recent Query Categories:[/bold]")
            recent_queries = self.session_history[-5:]  # Last 5 queries

            for i, entry in enumerate(recent_queries, 1):
                status_icon = "[green]✓[/green]" if entry.get("success") else "[red]✗[/red]"
                query_preview = entry["query"][:50] + "..." if len(entry["query"]) > 50 else entry["query"]
                console.print(f"  {status_icon} [{entry['timestamp']}] {query_preview}")

    def _toggle_tracing(self):
        """Toggle MCP tracing visibility."""
        self.mcp_tracing_enabled = not self.mcp_tracing_enabled

        if self.mcp_tracing_enabled:
            console.print("[green]✓ MCP tracing enabled[/green] - You'll see detailed communication traces")
        else:
            console.print("[yellow]⚠ MCP tracing disabled[/yellow] - Only final results will be shown")

        console.print("[dim]Note: This affects the verbosity of trace output during query execution[/dim]")


async def run_interactive_agent(config: AgentConfig):
    """Main entry point for interactive agent."""
    agent = InteractiveAgent(config)
    await agent.run_interactive_session()


if __name__ == "__main__":
    # For standalone execution
    import sys
    from pathlib import Path

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    config = AgentConfig.from_env()
    asyncio.run(run_interactive_agent(config))
