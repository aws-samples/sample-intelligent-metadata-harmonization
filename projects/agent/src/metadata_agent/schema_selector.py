# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Schema selection utilities for CLI."""

from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from rich.prompt import IntPrompt
from loguru import logger

from .http_client import MetadataAPIClient


class SchemaSelector:
    """Helper class for interactive schema selection in CLI."""

    def __init__(self, api_client: MetadataAPIClient):
        """Initialize with API client.

        Args:
            api_client: HTTP API client for schema operations
        """
        self.api_client = api_client
        self.console = Console()

    async def get_available_schemas(self) -> List[Dict[str, Any]]:
        """Get list of available schemas from API.

        Returns:
            List of schema dictionaries
        """
        try:
            return await self.api_client.list_schemas()
        except Exception as e:
            logger.error(f"❌ Failed to get schemas: {e}")
            return []

    def display_schema_selection_table(self, schemas: List[Dict[str, Any]]) -> None:
        """Display schemas in a rich table for selection.

        Args:
            schemas: List of schema dictionaries
        """
        if not schemas:
            self.console.print("[yellow]No schemas available[/yellow]")
            return

        table = Table(title="Available Schema Combinations")
        table.add_column("Index", justify="right", style="cyan", no_wrap=True)
        table.add_column("Core Schema", style="magenta", max_width=30)
        table.add_column("Program Schema", style="green", max_width=30)
        table.add_column("Description", style="yellow", max_width=50)

        # Flatten the schema combinations for display
        schema_combinations = []
        for core_schema in schemas:
            core_name = core_schema.get("name", "Unknown")
            core_id = core_schema.get("coreSchemaId", "")

            for program_schema in core_schema.get("programSchemas", []):
                program_name = program_schema.get("programName", "Unknown")
                program_id = program_schema.get("programSchemaId", "")

                schema_combinations.append(
                    {
                        "core_name": core_name,
                        "core_schema_id": core_id,
                        "program_name": program_name,
                        "program_schema_id": program_id,
                        "description": f"{core_name} + {program_name}",
                    }
                )

        for i, schema in enumerate(schema_combinations, 1):
            table.add_row(str(i), schema["core_name"], schema["program_name"], schema["description"])

        # Store flattened combinations for later use
        self._schema_combinations = schema_combinations

        self.console.print(table)

    def interactive_schema_selection(self, schemas: List[Dict[str, Any]]) -> Optional[tuple]:
        """Interactive schema selection with Rich interface.

        Args:
            schemas: List of available schemas (core schema objects from API)

        Returns:
            Tuple of (core_schema_id, program_schema_id) or None if cancelled
        """
        if not schemas:
            self.console.print("[red]❌ No schemas available for selection[/red]")
            return None

        # Display schemas and get flattened combinations
        self.display_schema_selection_table(schemas)

        # Use the flattened combinations for selection
        schema_combinations = getattr(self, "_schema_combinations", [])
        if not schema_combinations:
            self.console.print("[red]❌ No schema combinations available[/red]")
            return None

        # Get user selection
        try:
            while True:
                choice = IntPrompt.ask(
                    f"\nSelect schema combination (1-{len(schema_combinations)})", default=1, show_default=True
                )

                if 1 <= choice <= len(schema_combinations):
                    selected_schema = schema_combinations[choice - 1]
                    core_id = selected_schema.get("core_schema_id")
                    program_id = selected_schema.get("program_schema_id")

                    if core_id and program_id:
                        self.console.print(
                            f"[green]✅ Selected: {selected_schema.get('description', 'Selected schema')}[/green]"
                        )
                        return core_id, program_id
                    else:
                        self.console.print("[red]❌ Invalid schema data. Please try another selection.[/red]")
                else:
                    self.console.print(f"[red]❌ Please enter a number between 1 and {len(schema_combinations)}[/red]")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Schema selection cancelled[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"[red]❌ Selection error: {e}[/red]")
            return None

    async def select_schema_for_validation(self) -> Optional[tuple]:
        """Complete schema selection workflow with interactive selection.

        Returns:
            Tuple of (core_schema_id, program_schema_id) or None if cancelled/failed
        """
        # Get available schemas
        self.console.print("🔍 Loading available schemas...")
        schemas = await self.get_available_schemas()

        if not schemas:
            self.console.print("[red]❌ No schemas available from API[/red]")
            return None

        self.console.print(f"✅ Found {len(schemas)} available schema combinations")

        # Interactive selection only
        return self.interactive_schema_selection(schemas)
