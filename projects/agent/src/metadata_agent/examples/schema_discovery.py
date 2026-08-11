# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Schema discovery demo with test scenarios using AWS Strands Agent."""

import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ..main import MetadataAgent
from ..config import AgentConfig

console = Console()
logger = logging.getLogger(__name__)


class SchemaDiscoveryDemo:
    """Demo class for schema discovery capabilities with comprehensive test scenarios."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = MetadataAgent(config)
        self.discovered_schemas: List[Dict[str, Any]] = []
        self.schema_details_cache: Dict[str, Dict[str, Any]] = {}

    async def run_demo(self):
        """Run the complete schema discovery demo with enhanced test scenarios."""
        console.print(
            Panel(
                "[bold blue]Schema Discovery Demo[/bold blue]\n"
                "This demo showcases comprehensive schema exploration capabilities using natural language queries.\n"
                "Discover schemas, understand field requirements, and learn validation rules for different data types.",
                title="🔍 Schema Discovery & Exploration",
                border_style="blue",
            )
        )

        try:
            # Initialize the agent
            await self.agent.initialize()

            # Run comprehensive demo scenarios
            await self._run_comprehensive_scenarios()

            # Show schema comparison and analysis
            await self._run_schema_analysis()

            # Run data type validation scenarios
            if Confirm.ask("\nWould you like to explore schema requirements for different data types?"):
                await self.run_data_type_scenarios()

            # Interactive exploration
            if Confirm.ask("\nWould you like to try interactive schema exploration?"):
                await self._interactive_exploration()

        except Exception as e:
            console.print(f"[red]Demo failed:[/red] {e}")
            logger.exception("Schema discovery demo failed")
        finally:
            await self.agent.shutdown()

    async def _run_comprehensive_scenarios(self):
        """Run comprehensive demo scenarios with enhanced test cases."""
        console.print("\n[bold]Running Comprehensive Schema Discovery Scenarios[/bold]")

        scenarios = [
            {
                "title": "Schema Inventory Discovery",
                "query": "List all available schemas with their names, types, and descriptions. Show me what schemas I can use for validation.",
                "description": "Discover the complete inventory of available schemas",
                "category": "discovery",
            },
            {
                "title": "Core Schema Deep Dive",
                "query": "Get detailed information about core schemas including all field definitions, data types, validation rules, and required vs optional fields.",
                "description": "Explore core schema structure and field requirements in detail",
                "category": "analysis",
            },
            {
                "title": "Program Schema Analysis",
                "query": "Show me program schemas and explain how they extend or modify core schemas. What additional fields do they provide?",
                "description": "Understand program-specific schema extensions and modifications",
                "category": "analysis",
            },
            {
                "title": "Schema Compatibility Matrix",
                "query": "Which core and program schema combinations are valid for validation? Show me all possible combinations and their use cases.",
                "description": "Learn about valid schema combinations and their applications",
                "category": "compatibility",
            },
            {
                "title": "Patient Data Requirements",
                "query": "What are the specific field requirements for patient demographic data? Show me required fields, data types, formats, and validation rules.",
                "description": "Discover requirements for patient data validation scenarios",
                "category": "use_case",
            },
            {
                "title": "Laboratory Data Schema",
                "query": "What schemas and fields are needed for laboratory test results? Show me the data structure for lab data validation.",
                "description": "Explore laboratory data validation requirements",
                "category": "use_case",
            },
            {
                "title": "Date and Time Formats",
                "query": "What date and time formats are accepted in the schemas? Show me examples of valid date formats and timezone handling.",
                "description": "Understand temporal data format requirements",
                "category": "formats",
            },
            {
                "title": "Enumerated Values Discovery",
                "query": "What are the valid enumerated values for categorical fields? Show me allowed values for status, type, and classification fields.",
                "description": "Discover valid categorical values and enumerations",
                "category": "formats",
            },
            {
                "title": "Validation Rules Deep Dive",
                "query": "What validation rules are applied to different field types? Show me constraints, patterns, and business rules.",
                "description": "Understand comprehensive validation rule system",
                "category": "validation",
            },
            {
                "title": "Error Prevention Guide",
                "query": "What are the most common validation errors and how can I prevent them? Show me examples of data that would fail validation.",
                "description": "Learn about common validation pitfalls and prevention",
                "category": "troubleshooting",
            },
        ]

        # Group scenarios by category for better organization
        categories = {}
        for scenario in scenarios:
            category = scenario["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(scenario)

        # Run scenarios by category
        for category, category_scenarios in categories.items():
            console.print(f"\n[bold cyan]📋 {category.replace('_', ' ').title()} Scenarios[/bold cyan]")

            for i, scenario in enumerate(category_scenarios, 1):
                await self._run_enhanced_scenario(scenario, f"{category}_{i}")

                if i < len(category_scenarios):
                    if not Confirm.ask(f"\nContinue to next {category} scenario?", default=True):
                        break

            # Ask if user wants to continue to next category
            if category != list(categories.keys())[-1]:  # Not the last category
                if not Confirm.ask(
                    f"\nContinue to {list(categories.keys())[list(categories.keys()).index(category) + 1].replace('_', ' ').title()} scenarios?",
                    default=True,
                ):
                    break

    async def _run_enhanced_scenario(self, scenario: Dict[str, str], scenario_id: str):
        """Run a single enhanced demo scenario with detailed analysis."""
        console.print(f"\n[bold cyan]🔍 {scenario['title']}[/bold cyan]")
        console.print(f"[dim]{scenario['description']}[/dim]")

        # Display the query being executed
        query_panel = Panel(
            f"[bold]Natural Language Query:[/bold]\n{scenario['query']}",
            border_style="cyan",
            title="🤖 Agent Query",
            padding=(1, 2),
        )
        console.print(query_panel)

        # Execute the query
        try:
            response = await self.agent.execute_query(scenario["query"])

            # Cache schema information for later analysis
            if scenario["category"] == "discovery":
                self._cache_schema_discovery(response)
            elif scenario["category"] == "analysis":
                self._cache_schema_details(response, scenario["title"])

            # Display formatted response with enhanced formatting
            self._display_enhanced_schema_response(response, scenario["title"], scenario["category"])

            # Add scenario-specific insights
            self._display_scenario_insights(scenario, response)

        except Exception as e:
            console.print(f"[red]Scenario failed:[/red] {e}")
            logger.exception(f"Scenario {scenario_id} failed")

    def _display_enhanced_schema_response(self, response: str, title: str, category: str):
        """Display schema response with enhanced formatting based on category."""
        # Try to parse and format the response if it contains structured data
        if "schema" in response.lower() or "field" in response.lower():
            # Enhanced formatting for schema-related responses
            formatted_response = self._format_schema_info_enhanced(response, category)
        else:
            formatted_response = response

        # Choose border color based on category
        border_colors = {
            "discovery": "green",
            "analysis": "blue",
            "compatibility": "yellow",
            "use_case": "magenta",
            "formats": "cyan",
            "validation": "red",
            "troubleshooting": "orange",
        }
        border_color = border_colors.get(category, "green")

        response_panel = Panel(
            formatted_response, border_style=border_color, title=f"📋 {title} - Results", padding=(1, 2)
        )
        console.print(response_panel)

    def _format_schema_info_enhanced(self, response: str, category: str) -> str:
        """Format schema information with enhanced readability based on category."""
        lines = response.split("\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue

            # Category-specific formatting
            if category == "discovery":
                # Highlight schema names and counts
                if "schema" in line.lower() and (":" in line or "available" in line.lower()):
                    formatted_lines.append(f"[bold green]{line}[/bold green]")
                elif line.startswith("-") or line.startswith("•"):
                    formatted_lines.append(f"[cyan]{line}[/cyan]")
                else:
                    formatted_lines.append(line)

            elif category == "analysis":
                # Highlight field definitions and types
                if "field" in line.lower() or line.startswith("-") or line.startswith("•"):
                    formatted_lines.append(f"[blue]{line}[/blue]")
                elif "required" in line.lower():
                    formatted_lines.append(f"[red]{line}[/red]")
                elif "optional" in line.lower():
                    formatted_lines.append(f"[yellow]{line}[/yellow]")
                elif "type" in line.lower() or "format" in line.lower():
                    formatted_lines.append(f"[magenta]{line}[/magenta]")
                else:
                    formatted_lines.append(line)

            elif category == "validation":
                # Highlight validation rules and constraints
                if "rule" in line.lower() or "constraint" in line.lower():
                    formatted_lines.append(f"[red]{line}[/red]")
                elif "pattern" in line.lower() or "regex" in line.lower():
                    formatted_lines.append(f"[yellow]{line}[/yellow]")
                else:
                    formatted_lines.append(line)

            elif category == "formats":
                # Highlight format examples and patterns
                if "format" in line.lower() or "example" in line.lower():
                    formatted_lines.append(f"[cyan]{line}[/cyan]")
                elif "pattern" in line.lower():
                    formatted_lines.append(f"[yellow]{line}[/yellow]")
                else:
                    formatted_lines.append(line)

            else:
                # Default formatting
                if "schema" in line.lower() and ":" in line:
                    formatted_lines.append(f"[bold blue]{line}[/bold blue]")
                elif "field" in line.lower() or line.startswith("-"):
                    formatted_lines.append(f"[cyan]{line}[/cyan]")
                elif "required" in line.lower() or "type" in line.lower():
                    formatted_lines.append(f"[yellow]{line}[/yellow]")
                else:
                    formatted_lines.append(line)

        return "\n".join(formatted_lines)

    async def _run_schema_analysis(self):
        """Run schema comparison and analysis based on discovered information."""
        if not self.discovered_schemas and not self.schema_details_cache:
            console.print("[yellow]No schema information cached for analysis. Skipping analysis section.[/yellow]")
            return

        console.print("\n[bold magenta]📊 Schema Analysis & Comparison[/bold magenta]")

        # Display schema summary
        if self.discovered_schemas:
            self._display_schema_summary()

        # Run comparative analysis queries
        analysis_queries = [
            {
                "title": "Schema Comparison Analysis",
                "query": "Compare the core schemas and program schemas. What are the key differences in structure and required fields?",
                "description": "Understand structural differences between schema types",
            },
            {
                "title": "Field Overlap Analysis",
                "query": "Which fields are common across different schemas? Show me the shared field definitions and any variations.",
                "description": "Identify common fields and their variations",
            },
            {
                "title": "Validation Complexity Assessment",
                "query": "Which schemas have the most complex validation rules? Rank them by validation complexity and explain why.",
                "description": "Assess validation complexity across schemas",
            },
            {
                "title": "Data Type Distribution",
                "query": "What data types are most commonly used across all schemas? Show me the distribution of field types.",
                "description": "Analyze data type patterns across schemas",
            },
        ]

        for query_info in analysis_queries:
            if Confirm.ask(f"\nRun {query_info['title']}?", default=True):
                console.print(f"\n[bold cyan]🔬 {query_info['title']}[/bold cyan]")
                console.print(f"[dim]{query_info['description']}[/dim]")

                try:
                    response = await self.agent.execute_query(query_info["query"])

                    analysis_panel = Panel(
                        self._format_schema_info_enhanced(response, "analysis"),
                        border_style="magenta",
                        title=f"📊 {query_info['title']} - Results",
                        padding=(1, 2),
                    )
                    console.print(analysis_panel)

                except Exception as e:
                    console.print(f"[red]Analysis query failed:[/red] {e}")
                    logger.exception(f"Analysis query failed: {query_info['title']}")

    def _display_schema_summary(self):
        """Display a summary of discovered schemas."""
        console.print("\n[bold]📋 Discovered Schemas Summary[/bold]")

        if len(self.discovered_schemas) > 0:
            summary_table = Table(show_header=True, header_style="bold blue")
            summary_table.add_column("Schema", style="cyan", width=30)
            summary_table.add_column("Details Count", style="yellow", width=15)
            summary_table.add_column("Preview", style="white")

            for schema in self.discovered_schemas[:10]:  # Limit to first 10
                name = schema.get("name", "Unknown")[:30]
                details_count = len(schema.get("details", []))
                preview = (
                    " | ".join(schema.get("details", [])[:2])[:50] + "..."
                    if len(schema.get("details", [])) > 2
                    else " | ".join(schema.get("details", []))
                )

                summary_table.add_row(name, str(details_count), preview)

            console.print(summary_table)

            if len(self.discovered_schemas) > 10:
                console.print(f"[dim]... and {len(self.discovered_schemas) - 10} more schemas[/dim]")
        else:
            console.print("[yellow]No schemas discovered yet.[/yellow]")

    def _cache_schema_discovery(self, response: str):
        """Cache discovered schema information for later analysis."""
        # Try to extract schema information from response
        try:
            # Simple parsing to extract schema names and info
            lines = response.split("\n")
            current_schema = {}

            for line in lines:
                line = line.strip()
                if "schema" in line.lower() and ":" in line:
                    if current_schema:
                        self.discovered_schemas.append(current_schema)
                    current_schema = {"name": line, "details": []}
                elif line and current_schema:
                    current_schema["details"].append(line)

            if current_schema:
                self.discovered_schemas.append(current_schema)

        except Exception as e:
            logger.debug(f"Failed to cache schema discovery: {e}")

    def _cache_schema_details(self, response: str, title: str):
        """Cache detailed schema information for analysis."""
        try:
            self.schema_details_cache[title] = {"response": response, "timestamp": asyncio.get_event_loop().time()}
        except Exception as e:
            logger.debug(f"Failed to cache schema details: {e}")

    def _display_scenario_insights(self, scenario: Dict[str, str], response: str):
        """Display scenario-specific insights and tips."""
        insights = {
            "discovery": [
                "💡 Use schema names from this list in validation queries",
                "📝 Note the difference between core and program schemas",
                "🔗 Check which schemas can be combined for your use case",
            ],
            "analysis": [
                "🔍 Pay attention to required vs optional fields",
                "📊 Note the data types for proper formatting",
                "⚠️ Check validation rules to avoid common errors",
            ],
            "compatibility": [
                "🔗 Valid combinations ensure successful validation",
                "📋 Choose the right core/program pair for your data type",
                "✅ Test combinations with sample data first",
            ],
            "use_case": [
                "🎯 These requirements are specific to this data type",
                "📝 Use this as a checklist when preparing data",
                "🔄 Validate sample data to confirm understanding",
            ],
            "formats": [
                "📅 Follow exact format patterns for dates and times",
                "🔢 Check numeric precision and range requirements",
                "📝 Use provided examples as templates",
            ],
            "validation": [
                "⚠️ These rules prevent common data quality issues",
                "🛡️ Implement client-side validation using these rules",
                "🔧 Use validation feedback to improve data quality",
            ],
            "troubleshooting": [
                "🚨 These are the most frequent validation failures",
                "🔧 Implement data cleaning based on these patterns",
                "📊 Monitor these error types in your data pipeline",
            ],
        }

        category_insights = insights.get(scenario["category"], [])
        if category_insights:
            insights_text = "\n".join([f"  {insight}" for insight in category_insights])
            insights_panel = Panel(insights_text, title="💡 Key Insights", border_style="dim", padding=(0, 1))
            console.print(insights_panel)

    async def _interactive_exploration(self):
        """Allow enhanced interactive schema exploration with guided examples."""
        console.print("\n[bold]🎯 Interactive Schema Exploration[/bold]")
        console.print(
            "[dim]Enter natural language queries about schemas. Type 'quit' to exit, 'help' for guidance, or 'examples' for sample queries.[/dim]"
        )

        # Provide categorized example queries
        example_categories = {
            "Schema Discovery": [
                "What schemas are available for COVID-19 surveillance data?",
                "List all schemas related to patient demographics",
                "Show me schemas for laboratory test results",
                "What schemas support outbreak investigation data?",
            ],
            "Field Requirements": [
                "What are the required fields for patient contact information?",
                "Show me all date fields and their format requirements",
                "What numeric fields are available and what are their ranges?",
                "Which fields accept enumerated values and what are the options?",
            ],
            "Validation Rules": [
                "What validation rules apply to email addresses?",
                "How are phone numbers validated in the schemas?",
                "What are the constraints on age and date of birth fields?",
                "Show me validation patterns for identification numbers",
            ],
            "Data Formats": [
                "What date and time formats are accepted?",
                "How should I format addresses for validation?",
                "What are the accepted formats for laboratory values?",
                "Show me examples of properly formatted data",
            ],
            "Troubleshooting": [
                "What are common validation errors for patient data?",
                "How can I fix date format validation failures?",
                "What causes required field validation errors?",
                "Show me examples of data that would fail validation",
            ],
        }

        query_count = 0

        while True:
            try:
                console.print()
                query = Prompt.ask("[bold cyan]🔍 Enter your schema query[/bold cyan]")

                if query.lower() in ["quit", "exit", "q"]:
                    break
                elif query.lower() == "help":
                    self._display_interactive_help()
                    continue
                elif query.lower() == "examples":
                    self._display_example_queries(example_categories)
                    continue
                elif not query.strip():
                    continue

                # Execute the query
                query_count += 1
                console.print(f"\n[bold]Query #{query_count}:[/bold] {query}")

                response = await self.agent.execute_query(query)
                self._display_enhanced_schema_response(response, f"Interactive Query #{query_count}", "discovery")

                # Provide follow-up suggestions
                self._suggest_followup_queries(query, response)

            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting interactive mode...[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Query failed:[/red] {e}")
                logger.exception("Interactive query failed")

        console.print(f"\n[green]✓[/green] Interactive exploration completed. Executed {query_count} queries.")

    def _display_interactive_help(self):
        """Display help information for interactive mode."""
        help_panel = Panel(
            "[bold]Interactive Schema Exploration Help[/bold]\n\n"
            "[cyan]Available Commands:[/cyan]\n"
            "• Type any natural language question about schemas\n"
            "• 'examples' - Show categorized example queries\n"
            "• 'help' - Show this help message\n"
            "• 'quit', 'exit', or 'q' - Exit interactive mode\n\n"
            "[cyan]Tips for Better Results:[/cyan]\n"
            "• Be specific about the type of data you're working with\n"
            "• Ask about specific fields, formats, or validation rules\n"
            "• Use follow-up questions to dive deeper into topics\n"
            "• Ask for examples when you need concrete guidance",
            title="❓ Help",
            border_style="blue",
            padding=(1, 2),
        )
        console.print(help_panel)

    def _display_example_queries(self, example_categories: Dict[str, List[str]]):
        """Display categorized example queries."""
        console.print("\n[bold]📚 Example Queries by Category[/bold]")

        for category, examples in example_categories.items():
            console.print(f"\n[bold cyan]{category}:[/bold cyan]")
            for i, example in enumerate(examples, 1):
                console.print(f"  {i}. {example}")

        console.print(
            "\n[dim]Copy and paste any of these queries, or use them as inspiration for your own questions.[/dim]"
        )

    def _suggest_followup_queries(self, original_query: str, response: str):
        """Suggest relevant follow-up queries based on the current query and response."""
        # Simple keyword-based suggestions
        suggestions = []

        query_lower = original_query.lower()
        response_lower = response.lower()

        if "schema" in query_lower and "list" in query_lower:
            suggestions.extend(
                [
                    "Get detailed information about [specific schema name]",
                    "What fields are required in [schema name]?",
                    "Show me validation rules for [schema name]",
                ]
            )
        elif "field" in query_lower or "required" in query_lower:
            suggestions.extend(
                [
                    "What are the data types for these fields?",
                    "Show me validation examples for these fields",
                    "What are common errors with these fields?",
                ]
            )
        elif "format" in query_lower or "date" in query_lower:
            suggestions.extend(
                [
                    "Show me examples of valid data formats",
                    "What happens if I use the wrong format?",
                    "How do I convert my data to the correct format?",
                ]
            )
        elif "validation" in query_lower or "error" in query_lower:
            suggestions.extend(
                [
                    "How can I prevent these validation errors?",
                    "Show me examples of data that would pass validation",
                    "What tools can help me validate my data before submission?",
                ]
            )

        # Add schema-specific suggestions if schemas are mentioned in response
        if "schema" in response_lower:
            suggestions.append("Compare these schemas and show me their differences")

        if suggestions:
            suggestions_text = "\n".join([f"  • {suggestion}" for suggestion in suggestions[:3]])
            suggestions_panel = Panel(
                f"[bold]Suggested Follow-up Queries:[/bold]\n{suggestions_text}",
                title="💡 What's Next?",
                border_style="dim",
                padding=(0, 1),
            )
            console.print(suggestions_panel)

    async def run_data_type_scenarios(self):
        """Run test scenarios showing schema requirements for different data types."""
        console.print("\n[bold magenta]🧪 Data Type Validation Scenarios[/bold magenta]")
        console.print("[dim]These scenarios demonstrate schema requirements for common data types and use cases.[/dim]")

        data_type_scenarios = [
            {
                "title": "Patient Demographics Schema",
                "data_type": "Patient demographic information",
                "query": "What are the schema requirements for patient demographic data including name, age, gender, address, and contact information? Show me required fields and validation rules.",
                "test_data_hint": "Use patient_data_basic.csv or patient_data_complete.csv from test_data/valid/",
            },
            {
                "title": "Laboratory Results Schema",
                "data_type": "Laboratory test results",
                "query": "What schemas and field requirements are needed for laboratory test results including test names, values, units, reference ranges, and dates?",
                "test_data_hint": "Check test_data/valid/ for laboratory-related CSV files",
            },
            {
                "title": "Outbreak Investigation Schema",
                "data_type": "Disease outbreak investigation data",
                "query": "What are the schema requirements for outbreak investigation data including case definitions, exposure history, and epidemiological links?",
                "test_data_hint": "Use cyclospora_outbreak.csv from test_data/valid/",
            },
            {
                "title": "Surveillance Data Schema",
                "data_type": "Public health surveillance data",
                "query": "What schemas support public health surveillance data including case reporting, symptoms, and public health actions?",
                "test_data_hint": "Use covid_surveillance.csv from test_data/valid/",
            },
            {
                "title": "Temporal Data Requirements",
                "data_type": "Date and time fields",
                "query": "What are the specific requirements for date and time fields across all schemas? Show me accepted formats, timezone handling, and validation rules.",
                "test_data_hint": "Check invalid_date_formats.csv in test_data/invalid/ for common date errors",
            },
            {
                "title": "Categorical Data Validation",
                "data_type": "Enumerated and categorical fields",
                "query": "What categorical fields exist across schemas and what are their valid enumerated values? Show me status fields, classification fields, and type fields.",
                "test_data_hint": "Check invalid_enum_values.csv in test_data/invalid/ for enum validation errors",
            },
        ]

        for scenario in data_type_scenarios:
            if Confirm.ask(f"\nExplore {scenario['title']}?", default=True):
                console.print(f"\n[bold cyan]🔬 {scenario['title']}[/bold cyan]")
                console.print(f"[dim]Data Type: {scenario['data_type']}[/dim]")

                # Show test data hint
                test_hint_panel = Panel(
                    f"[bold]💡 Test Data Hint:[/bold]\n{scenario['test_data_hint']}",
                    border_style="yellow",
                    title="🗂️ Related Test Files",
                    padding=(0, 1),
                )
                console.print(test_hint_panel)

                try:
                    response = await self.agent.execute_query(scenario["query"])

                    scenario_panel = Panel(
                        self._format_schema_info_enhanced(response, "use_case"),
                        border_style="magenta",
                        title=f"📊 {scenario['title']} - Requirements",
                        padding=(1, 2),
                    )
                    console.print(scenario_panel)

                    # Show validation tips for this data type
                    self._show_data_type_tips(scenario["data_type"])

                except Exception as e:
                    console.print(f"[red]Scenario failed:[/red] {e}")
                    logger.exception(f"Data type scenario failed: {scenario['title']}")

    def _show_data_type_tips(self, data_type: str):
        """Show specific validation tips for different data types."""
        tips_map = {
            "Patient demographic information": [
                "Ensure all required demographic fields are present",
                "Validate date of birth format and reasonable age ranges",
                "Check address format and completeness",
                "Verify contact information format (phone, email)",
            ],
            "Laboratory test results": [
                "Include proper units for all numeric values",
                "Ensure test dates are in correct format",
                "Validate reference ranges are properly specified",
                "Check that test names match accepted terminology",
            ],
            "Disease outbreak investigation data": [
                "Verify case definitions match schema requirements",
                "Ensure exposure dates are chronologically consistent",
                "Check that epidemiological links are properly formatted",
                "Validate geographic information completeness",
            ],
            "Public health surveillance data": [
                "Confirm case reporting dates are valid",
                "Check symptom onset dates for consistency",
                "Validate public health action codes",
                "Ensure jurisdiction information is complete",
            ],
            "Date and time fields": [
                "Use ISO 8601 format (YYYY-MM-DD) for dates",
                "Include timezone information when required",
                "Ensure dates are chronologically consistent",
                "Validate date ranges are reasonable",
            ],
            "Enumerated and categorical fields": [
                "Use only values from the approved enumeration list",
                "Check case sensitivity requirements",
                "Ensure categorical mappings are consistent",
                "Validate that required categorical fields are not empty",
            ],
        }

        tips = tips_map.get(data_type, [])
        if tips:
            tips_text = "\n".join([f"  ✓ {tip}" for tip in tips])
            tips_panel = Panel(
                f"[bold]Validation Tips for {data_type}:[/bold]\n{tips_text}",
                title="💡 Best Practices",
                border_style="green",
                padding=(0, 1),
            )
            console.print(tips_panel)


async def run_schema_discovery(config: AgentConfig):
    """Main entry point for schema discovery demo."""
    demo = SchemaDiscoveryDemo(config)
    await demo.run_demo()


if __name__ == "__main__":
    # For standalone execution
    import sys

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    config = AgentConfig.from_env()
    asyncio.run(run_schema_discovery(config))
