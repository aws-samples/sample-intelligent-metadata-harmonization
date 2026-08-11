# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Main entry point for the Metadata Harmonization Agent."""

import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from loguru import logger
import logging

from strands import Agent

from .utils.logging_config import (
    configure_demo_logging,
    log_agent_startup,
    log_agent_shutdown,
    log_connection_status,
    log_tool_call,
    log_tool_response,
    log_error_with_context,
)
from .config import AgentConfig
from .streamable_http_client import StreamableHTTPMCPClient
from .session_state import AgentSessionState
from .dataframe_tools import DataFrameTools
from .proxy_tools import MCPProxyTools

# Set up rich console for demo appeal
console = Console()


# Custom formatter for Strands logging with emoji and timestamp
class StrandsEmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to Strands logging output."""

    def format(self, record):
        # Add emoji based on message content
        message = record.getMessage()

        if "Tool #" in message:
            # Tool execution logs get 🔧
            emoji_message = f"🔧 {message}"
        elif any(keyword in message.lower() for keyword in ["executing", "processing", "analyzing", "correcting"]):
            # LLM conversational output gets 🤖
            emoji_message = f"🤖 {message}"
        else:
            # Default for other Strands logs
            emoji_message = f"🔧 {message}"

        # Create new record with emoji message
        record.msg = emoji_message
        record.args = ()

        # Use loguru-style format with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # millisecond precision

        return (
            f"{timestamp} | {record.levelname:>8} | {record.name}:{record.funcName}:{record.lineno} - {emoji_message}"
        )


# Configure the root strands logger
strands_logger = logging.getLogger("strands")
strands_logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in strands_logger.handlers[:]:
    strands_logger.removeHandler(handler)

# Create custom handler with emoji formatter
strands_handler = logging.StreamHandler()
strands_handler.setFormatter(StrandsEmojiFormatter())
strands_logger.addHandler(strands_handler)

# Prevent propagation to avoid duplicate logs
strands_logger.propagate = False


class MetadataAgent:
    """Enhanced agent class for metadata harmonization with DataFrame tools and MCP proxy integration."""

    def __init__(
        self, config: AgentConfig, selected_core_id: Optional[str] = None, selected_program_id: Optional[str] = None
    ):
        """Initialize agent with session state and optional pre-selected schema IDs.

        Args:
            config: Agent configuration
            selected_core_id: Optional pre-selected core schema ID
            selected_program_id: Optional pre-selected program schema ID
        """
        self.config = config

        # Initialize session state and tools
        self.session_state = AgentSessionState()
        self.dataframe_tools = DataFrameTools(self.session_state)

        # MCP components
        self.mcp_client: Optional[StreamableHTTPMCPClient] = None
        self.proxy_tools: Optional[MCPProxyTools] = None
        self.strands_agent: Optional[Agent] = None
        self.available_tools: List[Dict[str, Any]] = []

        # Set pre-selected schema context if provided
        if selected_core_id and selected_program_id:
            self.session_state.set_schema_context(selected_core_id, selected_program_id)
            logger.info(f"🎯 Pre-selected schema context: {selected_core_id}/{selected_program_id}")

        logger.info("🤖 Enhanced MetadataAgent created with DataFrame tools and MCP proxy integration")

    def load_csv_file(self, csv_path: str) -> bool:
        """Load CSV file into the agent session state.

        Args:
            csv_path: Path to CSV file to load

        Returns:
            True if load was successful, False otherwise
        """
        return self.session_state.load_csv(csv_path)

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        return self.session_state.get_session_info()

    async def initialize(self):
        """Initialize the agent with direct MCPClient instantiation pattern."""
        log_agent_startup(
            {"mcp_url": self.config.mcp_url, "timeout": self.config.timeout, "has_auth": bool(self.config.mcp_pat)}
        )

        try:
            # Direct MCPClient instantiation following the example pattern
            logger.info("🔧 Creating StreamableHTTPMCPClient with direct instantiation")

            # Get headers for authentication (if needed)
            headers = self.config.get_headers()
            if headers:
                logger.info("🔐 Using authentication headers")
            else:
                logger.info("🌐 Connecting without authentication (local development)")

            # Create client using the simplified pattern
            self.mcp_client = StreamableHTTPMCPClient(
                url=self.config.mcp_url, headers=headers, timeout=self.config.timeout
            )

            logger.info("✅ StreamableHTTPMCPClient created successfully")

            # Connect and discover tools in one step
            await self._connect_and_discover_tools()

            # Create proxy tools
            self.proxy_tools = MCPProxyTools(self.session_state, self.mcp_client)

            # Create Strands Agent with both local DataFrame tools and MCP proxy tools
            self._create_strands_agent()

            logger.info(f"🎉 Agent initialized successfully with {len(self.available_tools)} tools")
            self._display_available_tools()

        except Exception as e:
            log_error_with_context(e, "agent initialization")
            raise

    async def _connect_and_discover_tools(self):
        """Connect to MCP server and discover available tools with simplified flow."""
        logger.info(f"🔗 Connecting to MCP server: {self.config.mcp_url}")

        try:
            # Direct connection using the streamable HTTP pattern
            await self.mcp_client.connect()
            log_connection_status(self.config.mcp_url, True)

            # Tool discovery with enhanced logging
            logger.info("🔍 Discovering available MCP tools...")
            log_tool_call("list_tools", {})

            tools_response = await self.mcp_client.list_tools()

            # Simple tool processing - just store the raw tools
            if tools_response:
                self.available_tools = tools_response
                logger.info(f"✅ Found {len(tools_response)} tools")
            else:
                self.available_tools = []
                logger.warning("⚠️  No tools found")

            log_tool_response("list_tools", True)

            if self.available_tools:
                tool_names = [getattr(tool, "tool_name", str(tool)) for tool in self.available_tools]
                logger.info(f"✅ Discovered {len(self.available_tools)} MCP tools: {tool_names}")
            else:
                logger.warning("⚠️  No MCP tools available - agent will have limited functionality")

        except Exception as e:
            log_connection_status(self.config.mcp_url, False, str(e))
            logger.error(f"💥 Failed to connect or discover tools: {e}")
            raise

    def _create_strands_agent(self):
        """Create AWS Strands Agent."""
        logger.info("� Creating AWS Strands Agent")

        # Collect all tool methods from DataFrame tools and proxy tools
        tools = []

        # Add DataFrame tool methods
        if self.dataframe_tools:
            dataframe_tool_methods = [
                self.dataframe_tools.get_dataframe_info,
                self.dataframe_tools.preview_dataframe,
                self.dataframe_tools.get_column_stats,
                self.dataframe_tools.search_dataframe,
                self.dataframe_tools.modify_cell,
                self.dataframe_tools.add_column,
                self.dataframe_tools.remove_column,
                self.dataframe_tools.rename_column,
                self.dataframe_tools.get_subsample,
                self.dataframe_tools.get_change_summary,
            ]
            tools.extend(dataframe_tool_methods)
            logger.info(f"📊 Added {len(dataframe_tool_methods)} DataFrame tools")

        # Add MCP proxy tool methods
        if self.proxy_tools:
            proxy_tool_methods = [
                self.proxy_tools.submit_metadata_validation,
                self.proxy_tools.list_schemas,
                self.proxy_tools.get_schema_details,
                self.proxy_tools.get_schema_columns,
                self.proxy_tools.get_validation_rules,
                self.proxy_tools.set_schema_context,
                self.proxy_tools.get_session_status,
                self.proxy_tools.clear_schema_context,
            ]
            tools.extend(proxy_tool_methods)
            logger.info(f"🔗 Added {len(proxy_tool_methods)} MCP proxy tools")

        # Create system prompt for metadata harmonization with iterative correction
        system_prompt = """You are a Metadata Harmonization Agent that validates and automatically corrects metadata using MCP tools.

CORE MISSION: When users provide metadata for validation, your job is to:
1. Check session status to see if schema context is already available
2. If no schema context exists, discover available schemas using list_schemas tool
3. Validate the metadata using submit_metadata_validation
4. If validation fails, analyze the errors returned by the tool
5. Automatically correct the metadata based on the specific errors
6. Resubmit the corrected metadata for validation
7. Repeat this process until the metadata passes validation
8. Show the user the final corrected metadata

CRITICAL: Smart Schema Context Management
- ALWAYS start by calling get_session_status() to check if schema context is already set
- If schema context is available (schema_context_available: true), proceed directly to validation
- If no schema context exists, then call list_schemas to discover what schemas are available
- NEVER assume schema names or UUIDs
- Use the exact UUIDs returned by list_schemas or from pre-selected context
- Let submit_metadata_validation tell you what errors exist
- Use get_schema_columns and get_validation_rules to understand requirements

ITERATIVE CORRECTION WORKFLOW:
1. **Check Session Status**: Call get_session_status() to see if schemas are already configured
2. **Schema Discovery (if needed)**: Only call list_schemas if no schema context exists
3. **Set Schema Context (if needed)**: Use set_schema_context() if schemas were discovered
4. **START WITH VALIDATION**: Call submit_metadata_validation immediately to get actual issues
5. **Analyze Errors**: Study the specific errors and recommendations returned by validation
6. **Make Corrections**: Fix the metadata based on the specific errors found
7. **Get More Details**: Use get_schema_columns and get_validation_rules only if needed for clarification
8. **Revalidate**: Call submit_metadata_validation again with corrected metadata
9. **Iterate**: Repeat steps 5-8 until validation passes or no more corrections are possible
10. **Present Results**: Show the final corrected metadata and validation status

ERROR CORRECTION STRATEGIES:
- Missing columns: Add required columns based on get_schema_columns results
- Invalid values: Replace with valid values based on get_validation_rules
- Format errors: Fix based on validation error messages
- Constraint violations: Adjust values to meet schema requirements
- Unknown columns: Remove or rename based on schema requirements

IMPORTANT BEHAVIORS:
- Rely entirely on MCP tools for schema discovery and error detection
- Never hardcode schema names or UUIDs
- Make corrections based on actual validation errors, not assumptions
- Continue iterating until submit_metadata_validation returns success
- Explain what corrections were made and why
- Respect pre-selected schema context when available

Your available tools:
- get_session_status(): Check current session status including schema context availability
- list_schemas(): Discover all available schema combinations with UUIDs (only if no context exists)
- set_schema_context(core_schema_id, program_schema_id): Set schema context for validation
- submit_metadata_validation(format): Validate current DataFrame (auto-injects content and schema IDs)
- get_schema_details(core_schema_id, program_schema_id): Get detailed schema information
- get_schema_columns(core_schema_id, program_schema_id): List expected columns
- get_validation_rules(core_schema_id, program_schema_id): Get validation rules

Always start with get_session_status() to check if schema context is already available."""

        self.strands_agent = Agent(
            name="Metadata Harmonization Agent",
            description="An AI agent for metadata validation and schema management",
            tools=tools,
            system_prompt=system_prompt,
            # model="us.amazon.nova-premier-v1:0"
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        )

        status = "with MCP tools" if tools else "without tools"
        logger.info(f"✅ Agent created {status}")

    def _display_available_tools(self):
        """Display available MCP tools."""
        if not self.available_tools:
            console.print("[yellow]⚠️  No tools available[/yellow]")
            return

        console.print(f"\n[bold blue]🔧 Available MCP Tools ({len(self.available_tools)}):[/bold blue]")

        for i, tool in enumerate(self.available_tools, 1):
            tool_name = getattr(tool, "tool_name", str(tool))
            console.print(f"  {i}. {tool_name}")

        logger.info(f"✅ Displayed {len(self.available_tools)} tools")

    async def execute_query(self, query: str) -> str:
        """Execute a natural language query using the simplified Strands agent."""
        if not self.strands_agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"💭 Processing query: {query}")
        logger.debug(f"📝 Query details: {query[:100]}{'...' if len(query) > 100 else ''}")

        try:
            import time

            start_time = time.time()

            logger.info("🤖 Executing query with AWS Strands Agent")

            # Direct execution using the simplified agent
            agent_result = self.strands_agent(query)

            duration_ms = (time.time() - start_time) * 1000

            # Extract response text from AgentResult
            response_text = str(agent_result)
            if hasattr(agent_result, "content"):
                response_text = agent_result.content
            elif hasattr(agent_result, "text"):
                response_text = agent_result.text
            elif hasattr(agent_result, "response"):
                response_text = agent_result.response

            logger.info(f"✅ Query completed successfully ({duration_ms:.1f}ms)")
            logger.debug(f"📤 Response preview: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")

            # Display response with demo-friendly formatting
            console.print(
                Panel(
                    f"[bold]Agent Response:[/bold]\n{response_text}",
                    border_style="green",
                    title="🤖 Metadata Harmonization Agent",
                    padding=(1, 2),
                )
            )

            return response_text

        except Exception as e:
            log_error_with_context(e, "query execution")
            logger.error(f"💥 Query failed after {(time.time() - start_time) * 1000:.1f}ms")
            raise

    async def shutdown(self):
        """Clean shutdown of the simplified agent."""
        logger.info("🔄 Shutting down Metadata Harmonization Agent...")

        # Clean shutdown of MCP client
        if self.mcp_client and self.mcp_client.is_connected:
            try:
                logger.info("🔌 Disconnecting MCP client...")
                await self.mcp_client.disconnect()
                logger.info("✅ MCP client disconnected successfully")
            except Exception as e:
                logger.warning(f"⚠️  Error during MCP client disconnect: {e}")

        # Clean up Strands agent
        if self.strands_agent:
            logger.info("🧹 Cleaning up Strands agent...")
            self.strands_agent = None

        log_agent_shutdown()
        logger.info("👋 Agent shutdown complete")


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Minimal logging output")
@click.pass_context
def cli(ctx, config: str, verbose: bool, quiet: bool):
    """Metadata Harmonization Agent - Validate and correct metadata using MCP tools."""

    # Configure demo-friendly logging with enhanced error handling
    try:
        if quiet:
            from .utils.logging_config import configure_quiet_logging

            configure_quiet_logging()
        else:
            log_level = "DEBUG" if verbose else "INFO"
            configure_demo_logging(log_level)

        logger.info("🚀 Starting Metadata Harmonization Agent CLI")

    except Exception as e:
        # Fallback to basic logging if logging config fails
        import sys

        print(f"ERROR: Failed to configure logging: {e}")
        # Set up basic console logging
        logger.remove()
        logger.add(sys.stdout, level="INFO", format="<level>{level}</level>: {message}")
        logger.info("🚀 Starting Metadata Harmonization Agent CLI (fallback logging)")

    # Enhanced configuration loading with comprehensive error handling
    agent_config = None
    config_errors = []

    try:
        # Always try environment variables first (following the example pattern)
        agent_config = AgentConfig.from_env()
        logger.info("📋 Configuration loaded from environment variables")

        # If using default URL and a config file is specified, merge file config
        if agent_config.mcp_url == "http://localhost:8080/agent/mcp" and config != "config.yaml":
            try:
                file_config = AgentConfig.from_file(config)
                # Only override if file has different values
                if file_config.mcp_url != "http://localhost:8080/agent/mcp":
                    agent_config.mcp_url = file_config.mcp_url
                    logger.info(f"📁 Merged configuration from file: {config}")
            except FileNotFoundError:
                logger.debug(f"Config file {config} not found, using environment/defaults")
            except yaml.YAMLError as e:
                config_errors.append(f"Invalid YAML in {config}: {e}")
                logger.warning(f"⚠️  Invalid YAML in config file {config}: {e}")
            except Exception as e:
                config_errors.append(f"Could not load config file {config}: {e}")
                logger.debug(f"Could not load config file {config}: {e}")

    except Exception as e:
        config_errors.append(f"Environment config failed: {e}")
        logger.warning(f"⚠️  Environment config failed: {e}")

        # Fallback to file-based config
        try:
            agent_config = AgentConfig.from_file(config)
            logger.info(f"📁 Configuration loaded from file: {config}")
        except FileNotFoundError:
            logger.warning(f"⚠️  Config file {config} not found, using defaults")
            agent_config = AgentConfig()
        except yaml.YAMLError as e:
            config_errors.append(f"Invalid YAML in {config}: {e}")
            logger.error(f"💥 Invalid YAML in config file {config}: {e}")
            agent_config = AgentConfig()
        except Exception as e:
            config_errors.append(f"Failed to load config file {config}: {e}")
            logger.error(f"💥 Failed to load config file {config}: {e}")
            agent_config = AgentConfig()

    # Ensure we have a valid config
    if agent_config is None:
        logger.error("💥 Failed to load configuration from all sources, using defaults")
        agent_config = AgentConfig()

    # Validate configuration with actionable error messages
    validation_errors = _validate_config(agent_config)
    if validation_errors:
        logger.warning("⚠️  Configuration validation issues found:")
        for error in validation_errors:
            logger.warning(f"   • {error}")

    # Log configuration for demo purposes with enhanced formatting
    logger.info(f"🌐 MCP Server: {agent_config.mcp_url}")
    logger.info(f"🔐 Authentication: {'Enabled' if agent_config.mcp_pat else 'Disabled (local dev)'}")
    logger.info(f"⏱️  Timeout: {agent_config.timeout}s")
    logger.info(f"📊 Log Level: {agent_config.log_level}")

    # Store config and any errors for commands to access
    ctx.ensure_object(dict)
    ctx.obj["config"] = agent_config
    ctx.obj["config_errors"] = config_errors
    ctx.obj["validation_errors"] = validation_errors


def _validate_config(config: AgentConfig) -> list[str]:
    """Validate configuration and return list of issues with actionable messages."""
    errors = []

    # Validate MCP URL format
    if not config.mcp_url.startswith(("http://", "https://")):
        errors.append(f"Invalid MCP URL format: {config.mcp_url}. Must start with http:// or https://")

    # Validate timeout
    if config.timeout <= 0:
        errors.append(f"Invalid timeout: {config.timeout}. Must be positive number of seconds")
    elif config.timeout < 5:
        errors.append(f"Very short timeout: {config.timeout}s. Consider using at least 10s for reliable connections")
    elif config.timeout > 300:
        errors.append(f"Very long timeout: {config.timeout}s. Consider using less than 300s to avoid hanging")

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_levels:
        errors.append(f"Invalid log level: {config.log_level}. Must be one of: {', '.join(valid_levels)}")

    # Check test data directory
    if config.test_data_dir and not Path(config.test_data_dir).exists():
        errors.append(f"Test data directory not found: {config.test_data_dir}. Some demo features may not work")

    return errors


@cli.command()
@click.argument("metadata_file", type=click.Path(exists=True))
@click.option("--core-schema", help="Core schema ID (optional)")
@click.option("--program-schema", help="Program schema ID (optional)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive schema selection")
@click.option("--format", "-f", default="csv", type=click.Choice(["csv", "json"]), help="Metadata format")
@click.pass_context
def validate(
    ctx, metadata_file: str, core_schema: Optional[str], program_schema: Optional[str], interactive: bool, format: str
):
    """Enhanced validation workflow with schema pre-selection and DataFrame tools."""
    config = ctx.obj["config"]

    async def run_enhanced_validation():
        """Run enhanced validation with schema selection and DataFrame tools."""
        console.print("📄 [bold blue]Enhanced Metadata Validation Workflow[/bold blue]")
        console.print(f"File: {metadata_file}")

        # Step 1: Schema Selection (if not provided)
        selected_core_id = core_schema
        selected_program_id = program_schema

        if not (selected_core_id and selected_program_id):
            from .http_client import MetadataAPIClient
            from .schema_selector import SchemaSelector

            console.print("\n🔍 [bold]Step 1: Schema Selection[/bold]")

            # Create HTTP client for schema selection
            api_client = MetadataAPIClient(config.api_base_url, config.timeout)
            selector = SchemaSelector(api_client)

            try:
                if interactive:
                    # Interactive schema selection
                    console.print("Interactive schema selection mode")
                    schema_result = await selector.select_schema_for_validation()
                else:
                    # Let agent discover schemas
                    console.print("Agent will discover appropriate schemas")
                    schema_result = None

                if schema_result:
                    selected_core_id, selected_program_id = schema_result
                    console.print(f"[green]✅ Schema context: {selected_core_id}/{selected_program_id}[/green]")

            finally:
                await api_client.close()

        # Step 2: Initialize Agent with Schema Context
        console.print("\n🤖 [bold]Step 2: Initialize Enhanced Agent[/bold]")
        agent = MetadataAgent(config, selected_core_id, selected_program_id)

        try:
            await agent.initialize()

            # Step 3: Load CSV into Agent
            console.print("\n📊 [bold]Step 3: Load CSV Data[/bold]")
            if not agent.load_csv_file(metadata_file):
                console.print(f"[red]❌ Failed to load CSV file: {metadata_file}[/red]")
                return

            # Show session status
            session_info = agent.get_session_info()
            df_info = session_info["dataframe"]
            schema_context = session_info["schema_context"]

            console.print(f"✅ CSV loaded: {df_info['shape'][0]} rows, {df_info['shape'][1]} columns")
            if schema_context["has_schema_context"]:
                console.print(
                    f"✅ Schema context ready: {schema_context['core_schema_id']}/{schema_context['program_schema_id']}"
                )
            else:
                console.print("⚠️  No schema context - agent will need to discover schemas")

            # Step 4: Enhanced Validation Workflow
            console.print("\n🔧 [bold]Step 4: AI-Powered Validation & Correction[/bold]")

            if schema_context["has_schema_context"]:
                # Schema context available - direct validation
                query = f"""
                I have loaded a CSV file for metadata validation with the following information:

                CSV File: {metadata_file}
                Rows: {df_info['shape'][0]}
                Columns: {df_info['shape'][1]}
                Schema Context: Already set

                Please follow this enhanced workflow:

                1. Use get_dataframe_info() to understand the current DataFrame structure
                2. Use preview_dataframe() to see sample data
                3. Use submit_metadata_validation() to validate (DataFrame and schemas auto-injected)
                4. If validation fails, analyze the specific errors returned
                5. Use DataFrame tools to make targeted corrections:
                   - modify_cell() for individual cell fixes
                   - add_column() for missing required columns
                   - rename_column() for naming issues
                   - remove_column() for unwanted columns
                6. Re-validate with submit_metadata_validation() after each correction
                7. Continue until validation passes or no more improvements possible
                8. Use get_change_summary() to show what was modified

                The DataFrame content and schema IDs are automatically injected - you don't need to provide them.
                Start by examining the DataFrame and then validating it.
                """
            else:
                # No schema context - agent needs to discover
                query = f"""
                I have loaded a CSV file for metadata validation. The DataFrame is ready but no schema context is set.

                CSV File: {metadata_file}
                Rows: {df_info['shape'][0]}
                Columns: {df_info['shape'][1]}

                Please follow this discovery and validation workflow:

                1. Use get_dataframe_info() to understand the DataFrame structure
                2. Use preview_dataframe() to see sample data
                3. Use list_schemas() to discover available schema combinations
                4. Choose appropriate schemas and use set_schema_context(core_id, program_id)
                5. Use submit_metadata_validation() to validate (DataFrame auto-injected)
                6. If validation fails, analyze errors and use DataFrame tools for corrections
                7. Continue validation and correction cycles until successful
                8. Use get_change_summary() to show final modifications

                Start by examining the DataFrame, then discover and set appropriate schemas.
                """

            await agent.execute_query(query)

            # Step 5: Show Final Results
            console.print("\n📋 [bold]Step 5: Validation Complete[/bold]")
            final_session_info = agent.get_session_info()
            console.print(f"Final operation count: {final_session_info['operation_count']}")

            logger.info("✅ Enhanced validation workflow completed")

        except Exception as e:
            logger.error(f"💥 Enhanced validation failed: {e}")
            console.print(f"[red]❌ Validation failed: {e}[/red]")
        finally:
            await agent.shutdown()

    try:
        asyncio.run(run_enhanced_validation())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Validation interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")


@cli.command()
@click.pass_context
def list_schemas(ctx):
    """List available schemas using HTTP API."""
    config = ctx.obj["config"]

    async def run_list_schemas():
        """List schemas via HTTP API."""
        from .http_client import MetadataAPIClient
        from .schema_selector import SchemaSelector

        console.print("🔍 [bold blue]Available Schema Combinations[/bold blue]")

        api_client = MetadataAPIClient(config.api_base_url, config.timeout)
        selector = SchemaSelector(api_client)

        try:
            schemas = await selector.get_available_schemas()

            if schemas:
                selector.display_schema_selection_table(schemas)
                console.print(f"\n✅ Found {len(schemas)} schema combinations")
            else:
                console.print("[yellow]No schemas available from API[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ Failed to list schemas: {e}[/red]")
            logger.error(f"Schema listing failed: {e}")
        finally:
            await api_client.close()

    try:
        asyncio.run(run_list_schemas())
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Command failed: {e}[/red]")


@cli.command()
@click.pass_context
def discover(ctx):
    """Run schema discovery demo with simplified agent."""
    config = ctx.obj["config"]
    config_errors = ctx.obj.get("config_errors", [])

    logger.info("🗂️  Starting schema discovery demo")

    # Check for configuration issues
    if config_errors:
        logger.warning("⚠️  Configuration issues detected - discovery may have limited functionality")

    try:
        # Pre-flight checks
        if not _check_demo_prerequisites(config):
            logger.error("💥 Demo prerequisites not met")
            console.print("\n[red]❌ Schema discovery demo cannot run[/red]")
            console.print("[yellow]💡 Check MCP server connectivity and configuration[/yellow]")
            return

        from .examples.schema_discovery import run_schema_discovery

        asyncio.run(run_schema_discovery(config))
        logger.info("✅ Schema discovery demo completed successfully")

    except ImportError as e:
        logger.error(f"💥 Missing demo dependencies: {e}")
        console.print(f"[red]❌ Demo module not found:[/red] {e}")

    except ConnectionError as e:
        logger.error(f"💥 Connection failed: {e}")
        console.print(f"[red]❌ Cannot connect to MCP server:[/red] {e}")
        console.print("[yellow]💡 Schema discovery requires active MCP connection[/yellow]")
        console.print(f"   • Verify server is running at {config.mcp_url}")
        console.print("   • Check authentication if required")

    except TimeoutError as e:
        logger.error(f"💥 Discovery timed out: {e}")
        console.print(f"[red]❌ Schema discovery timed out:[/red] {e}")
        console.print("[yellow]💡 Schema queries can be complex - try increasing timeout[/yellow]")

    except KeyboardInterrupt:
        logger.info("⚠️  Schema discovery interrupted by user")
        console.print("\n[yellow]⚠️  Discovery interrupted by user[/yellow]")

    except Exception as e:
        logger.error(f"💥 Schema discovery demo failed: {e}")
        console.print(f"[red]❌ Schema discovery failed:[/red] {e}")
        console.print("[yellow]💡 This might indicate MCP server or schema issues[/yellow]")
        if ctx.params.get("verbose"):
            logger.exception("Full error details:")
        else:
            console.print("   • Run with --verbose for detailed error information")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Run interactive agent with simplified architecture."""
    config = ctx.obj["config"]
    config_errors = ctx.obj.get("config_errors", [])

    logger.info("🤖 Starting interactive agent session")

    # Show configuration status
    if config_errors:
        logger.warning("⚠️  Configuration issues detected - some features may be limited")
        console.print("[yellow]⚠️  Configuration issues detected:[/yellow]")
        for error in config_errors[:2]:
            console.print(f"   • {error}")
        console.print("[dim]Interactive mode will continue with available functionality[/dim]\n")

    try:
        # Enhanced pre-flight checks for interactive mode
        connectivity_ok = _check_demo_prerequisites(config, silent=True)
        if not connectivity_ok:
            logger.warning("⚠️  MCP connectivity issues - interactive mode will have limited functionality")
            console.print("[yellow]⚠️  MCP server connectivity issues detected[/yellow]")
            console.print("[dim]Interactive mode will start but some features may not work[/dim]")

            if not Confirm.ask("Continue anyway?", default=True):
                console.print("[yellow]Interactive session cancelled[/yellow]")
                return

        from .examples.interactive_agent import run_interactive_agent

        asyncio.run(run_interactive_agent(config))
        logger.info("✅ Interactive agent session completed successfully")

    except ImportError as e:
        logger.error(f"💥 Missing interactive dependencies: {e}")
        console.print(f"[red]❌ Interactive module not found:[/red] {e}")
        console.print("[yellow]💡 This might be a development environment issue[/yellow]")

    except ConnectionError as e:
        logger.error(f"💥 Connection failed during interactive session: {e}")
        console.print(f"[red]❌ Lost connection to MCP server:[/red] {e}")
        console.print("[yellow]💡 Interactive session requires stable MCP connection[/yellow]")

    except KeyboardInterrupt:
        logger.info("⚠️  Interactive session interrupted by user")
        console.print("\n[yellow]👋 Interactive session ended by user[/yellow]")

    except Exception as e:
        logger.error(f"💥 Interactive agent session failed: {e}")
        console.print(f"[red]❌ Interactive session failed:[/red] {e}")
        console.print("[yellow]💡 Troubleshooting:[/yellow]")
        console.print("   • Check MCP server status")
        console.print("   • Verify configuration settings")
        console.print("   • Try restarting the session")
        if ctx.params.get("verbose"):
            logger.exception("Full error details:")
        else:
            console.print("   • Use --verbose for detailed error information")


@cli.command()
@click.argument("query", required=False)
@click.option("--timeout", "-t", type=int, help="Override default timeout for this query")
@click.pass_context
def query(ctx, query: Optional[str], timeout: Optional[int]):
    """Execute a natural language query using the simplified AWS Strands agent."""
    config = ctx.obj["config"]
    config_errors = ctx.obj.get("config_errors", [])

    # Override timeout if specified
    if timeout:
        config.timeout = timeout
        logger.info(f"⏱️  Using custom timeout: {timeout}s")

    async def run_query():
        """Run query with enhanced error handling and graceful degradation."""
        logger.info("🎯 Starting query execution")

        # Show configuration warnings if any
        if config_errors:
            logger.warning("⚠️  Configuration issues may affect query performance")

        # Direct agent instantiation following the example pattern
        agent = MetadataAgent(config)
        query_text = None

        try:
            # Initialize with enhanced error handling
            logger.info("🔧 Initializing agent...")
            await agent.initialize()

            # Get query from user if not provided
            if not query:
                console.print("\n[bold blue]💭 Enter your query:[/bold blue]")
                console.print(
                    "[dim]Examples: 'List available schemas', 'Validate my CSV data', 'Help with date formats'[/dim]"
                )
                try:
                    query_text = click.prompt("Query", type=str)
                except click.Abort:
                    console.print("\n[yellow]Query cancelled[/yellow]")
                    return
            else:
                query_text = query

            if not query_text or not query_text.strip():
                console.print("[yellow]⚠️  Empty query provided[/yellow]")
                return

            logger.info(f"🔍 Executing query: {query_text}")

            # Execute with the simplified agent and enhanced error handling
            try:
                await agent.execute_query(query_text)
                logger.info("✅ Query execution completed successfully")

            except TimeoutError as e:
                logger.error(f"💥 Query timed out after {config.timeout}s: {e}")
                console.print(f"[red]❌ Query timed out after {config.timeout}s[/red]")
                console.print("[yellow]💡 Try:[/yellow]")
                console.print("   • Use --timeout flag to increase timeout")
                console.print("   • Simplify your query")
                console.print("   • Check MCP server performance")

            except ConnectionError as e:
                logger.error(f"💥 Connection lost during query: {e}")
                console.print(f"[red]❌ Lost connection to MCP server:[/red] {e}")
                console.print("[yellow]💡 The MCP server may have disconnected during processing[/yellow]")

            except ValueError as e:
                logger.error(f"💥 Invalid query or response: {e}")
                console.print(f"[red]❌ Query processing error:[/red] {e}")
                console.print("[yellow]💡 Try rephrasing your query or check for typos[/yellow]")

        except ConnectionError as e:
            logger.error(f"💥 Failed to connect to MCP server: {e}")
            console.print(f"[red]❌ Cannot connect to MCP server:[/red] {e}")
            console.print("[yellow]💡 Solutions:[/yellow]")
            console.print(f"   • Check if MCP server is running at {config.mcp_url}")
            console.print("   • Verify network connectivity")
            console.print("   • Check authentication credentials")

        except TimeoutError as e:
            logger.error(f"💥 Agent initialization timed out: {e}")
            console.print(f"[red]❌ Agent initialization timed out:[/red] {e}")
            console.print("[yellow]💡 The MCP server may be slow to respond[/yellow]")
            console.print(f"   • Try increasing timeout with --timeout (current: {config.timeout}s)")

        except ImportError as e:
            logger.error(f"💥 Missing dependencies: {e}")
            console.print(f"[red]❌ Missing required dependencies:[/red] {e}")
            console.print("[yellow]💡 This might be an installation issue[/yellow]")

        except KeyboardInterrupt:
            logger.info("⚠️  Query interrupted by user")
            console.print("\n[yellow]⚠️  Query interrupted by user[/yellow]")

        except Exception as e:
            logger.error(f"💥 Query execution failed: {e}")
            console.print(f"[red]❌ Query execution failed:[/red] {e}")

            # Provide context-specific troubleshooting
            if query_text:
                console.print("[yellow]💡 Troubleshooting this query:[/yellow]")
                if "validate" in query_text.lower():
                    console.print("   • Ensure your data file exists and is accessible")
                    console.print("   • Check data format and schema compatibility")
                elif "schema" in query_text.lower():
                    console.print("   • Verify MCP server has schema information available")
                    console.print("   • Try a simpler schema query first")
                else:
                    console.print("   • Try a simpler query to test connectivity")
                    console.print("   • Check query syntax and spelling")

            console.print("   • Use --verbose for detailed error information")
            if ctx.params.get("verbose"):
                logger.exception("Full error details:")

        finally:
            # Always attempt cleanup
            try:
                await agent.shutdown()
            except Exception as e:
                logger.debug(f"Error during agent shutdown: {e}")

    asyncio.run(run_query())


@cli.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed tool information")
@click.pass_context
def tools(ctx, detailed: bool):
    """List available MCP tools using simplified client."""
    config = ctx.obj["config"]
    config_errors = ctx.obj.get("config_errors", [])

    async def list_tools():
        """List tools with enhanced error handling and detailed output options."""
        logger.info("🔧 Discovering available MCP tools")

        # Show configuration warnings
        if config_errors:
            logger.warning("⚠️  Configuration issues may affect tool discovery")
            console.print("[yellow]⚠️  Configuration issues detected - tool discovery may be limited[/yellow]")

        # Direct agent instantiation
        agent = MetadataAgent(config)
        try:
            # Initialize with connection status feedback
            console.print(f"[dim]Connecting to MCP server at {config.mcp_url}...[/dim]")
            await agent.initialize()

            # Enhanced tool display
            if agent.available_tools:
                console.print(f"\n[bold green]✅ Found {len(agent.available_tools)} MCP tools[/bold green]")

                if detailed:
                    # Show detailed tool information
                    console.print("\n[bold blue]📋 Detailed Tool Information:[/bold blue]")
                    for i, tool in enumerate(agent.available_tools, 1):
                        tool_panel = Panel(
                            f"[bold cyan]Name:[/bold cyan] {tool['name']}\n"
                            f"[bold cyan]Description:[/bold cyan] {tool['description']}\n"
                            f"[bold cyan]Parameters:[/bold cyan] {len(tool.get('parameters', {}))} defined",
                            title=f"Tool {i}",
                            border_style="blue",
                            padding=(0, 1),
                        )
                        console.print(tool_panel)
                else:
                    # Show summary list
                    console.print("\n[bold blue]Available Tools:[/bold blue]")
                    for i, tool in enumerate(agent.available_tools, 1):
                        console.print(f"  {i:2d}. [cyan]{tool['name']}[/cyan] - {tool['description']}")
                    console.print("\n[dim]💡 Use --detailed flag for more information about each tool[/dim]")

            else:
                console.print("\n[yellow]⚠️  No MCP tools available[/yellow]")
                console.print("[yellow]💡 Possible reasons:[/yellow]")
                console.print("   • MCP server has no tools configured")
                console.print("   • Authentication issues preventing tool access")
                console.print("   • Server configuration problems")
                console.print("   • Network connectivity issues")

        except ConnectionError as e:
            logger.error(f"💥 Cannot connect to MCP server: {e}")
            console.print(f"[red]❌ Cannot connect to MCP server:[/red] {e}")
            console.print("[yellow]💡 Tool discovery requires MCP server connection:[/yellow]")
            console.print(f"   • Check if server is running at {config.mcp_url}")
            console.print("   • Verify network connectivity")
            console.print("   • Check authentication credentials")

        except TimeoutError as e:
            logger.error(f"💥 Tool discovery timed out: {e}")
            console.print(f"[red]❌ Tool discovery timed out:[/red] {e}")
            console.print("[yellow]💡 Server may be slow to respond:[/yellow]")
            console.print(f"   • Current timeout: {config.timeout}s")
            console.print("   • Try increasing timeout in configuration")
            console.print("   • Check server performance")

        except ValueError as e:
            logger.error(f"💥 Invalid server response: {e}")
            console.print(f"[red]❌ Invalid response from MCP server:[/red] {e}")
            console.print("[yellow]💡 Server may have compatibility issues:[/yellow]")
            console.print("   • Check MCP server version")
            console.print("   • Verify server configuration")

        except Exception as e:
            logger.error(f"💥 Tool discovery failed: {e}")
            console.print(f"[red]❌ Tool discovery failed:[/red] {e}")
            console.print("[yellow]💡 Troubleshooting:[/yellow]")
            console.print("   • Check MCP server logs for errors")
            console.print("   • Verify agent configuration")
            console.print("   • Try restarting the MCP server")
            if ctx.params.get("verbose"):
                logger.exception("Full error details:")
            else:
                console.print("   • Use --verbose for detailed error information")

        finally:
            try:
                await agent.shutdown()
            except Exception as e:
                logger.debug(f"Error during agent shutdown: {e}")

    asyncio.run(list_tools())


def _check_demo_prerequisites(config: AgentConfig, silent: bool = False) -> bool:
    """Check if demo prerequisites are met for reliable operation."""
    issues = []

    # Check MCP URL format
    if not config.mcp_url.startswith(("http://", "https://")):
        issues.append(f"Invalid MCP URL format: {config.mcp_url}")

    # Check if URL looks like a local development server
    if "localhost" in config.mcp_url or "127.0.0.1" in config.mcp_url:
        if not silent:
            logger.debug("🏠 Using local MCP server - ensure it's running")

    # Check timeout is reasonable
    if config.timeout < 5:
        issues.append(f"Very short timeout ({config.timeout}s) may cause connection issues")

    # Check test data directory for demos that need it
    if config.test_data_dir and not Path(config.test_data_dir).exists():
        if not silent:
            logger.debug(f"📁 Test data directory not found: {config.test_data_dir}")

    # Log issues if not silent
    if issues and not silent:
        logger.warning("⚠️  Demo prerequisite issues:")
        for issue in issues:
            logger.warning(f"   • {issue}")

    # Return True if no critical issues (URL format is the only critical one)
    critical_issues = [issue for issue in issues if "Invalid MCP URL format" in issue]
    return len(critical_issues) == 0


def _format_error_for_user(error: Exception, context: str = "") -> str:
    """Format error messages in a user-friendly way with actionable advice."""
    error_type = type(error).__name__
    error_msg = str(error)

    # Common error patterns and user-friendly explanations
    if isinstance(error, ConnectionError):
        if "Connection refused" in error_msg:
            return "Cannot connect to MCP server - it may not be running or accessible"
        elif "timeout" in error_msg.lower():
            return "Connection timed out - server may be slow or unreachable"
        else:
            return f"Network connection problem: {error_msg}"

    elif isinstance(error, TimeoutError):
        return "Operation timed out - server may be overloaded or slow"

    elif isinstance(error, ValueError):
        if "Invalid" in error_msg:
            return f"Configuration or data format issue: {error_msg}"
        else:
            return f"Data validation error: {error_msg}"

    elif isinstance(error, ImportError):
        return f"Missing required component: {error_msg}"

    elif isinstance(error, FileNotFoundError):
        return f"Required file not found: {error_msg}"

    elif isinstance(error, PermissionError):
        return f"Permission denied: {error_msg}"

    else:
        # Generic error with context
        if context:
            return f"{error_type} during {context}: {error_msg}"
        else:
            return f"{error_type}: {error_msg}"


@cli.command()
@click.pass_context
def health(ctx):
    """Check agent and MCP server health status."""
    config = ctx.obj["config"]

    async def check_health():
        """Perform comprehensive health checks."""
        logger.info("🏥 Starting health check")
        console.print("[bold blue]🏥 Agent Health Check[/bold blue]\n")

        # Configuration health
        console.print("[bold]📋 Configuration Status:[/bold]")
        config_errors = ctx.obj.get("config_errors", [])
        validation_errors = ctx.obj.get("validation_errors", [])

        if not config_errors and not validation_errors:
            console.print("   ✅ Configuration is valid")
        else:
            console.print("   ⚠️  Configuration issues detected:")
            for error in (config_errors + validation_errors)[:5]:
                console.print(f"      • {error}")

        console.print(f"   • MCP URL: {config.mcp_url}")
        console.print(f"   • Timeout: {config.timeout}s")
        console.print(f"   • Authentication: {'Enabled' if config.mcp_pat else 'Disabled'}")

        # MCP Server connectivity
        console.print("\n[bold]🌐 MCP Server Connectivity:[/bold]")
        agent = MetadataAgent(config)

        try:
            console.print(f"   🔍 Testing connection to {config.mcp_url}...")
            await agent.initialize()

            console.print("   ✅ Successfully connected to MCP server")
            console.print(f"   ✅ Discovered {len(agent.available_tools)} MCP tools")

            # Test a simple tool call if tools are available
            if agent.available_tools:
                console.print("   🔧 Testing tool functionality...")
                try:
                    # This would be a simple test query
                    await agent.execute_query("List available schemas")
                    console.print("   ✅ Tool execution test successful")
                except Exception as e:
                    console.print(f"   ⚠️  Tool execution test failed: {_format_error_for_user(e)}")
            else:
                console.print("   ⚠️  No tools available for testing")

        except Exception as e:
            console.print(f"   ❌ Connection failed: {_format_error_for_user(e)}")
            console.print("   💡 Check if MCP server is running and accessible")

        finally:
            await agent.shutdown()

        # Environment checks
        console.print("\n[bold]🔧 Environment Status:[/bold]")

        # Check test data
        if config.test_data_dir:
            test_data_path = Path(config.test_data_dir)
            if test_data_path.exists():
                csv_files = list(test_data_path.rglob("*.csv"))
                console.print(f"   ✅ Test data directory found with {len(csv_files)} CSV files")
            else:
                console.print(f"   ⚠️  Test data directory not found: {config.test_data_dir}")

        # Check dependencies
        try:
            import yaml  # noqa: F401
            import rich  # noqa: F401
            from strands import Agent  # noqa: F401

            console.print("   ✅ All required dependencies available")
        except ImportError as e:
            console.print(f"   ❌ Missing dependency: {e}")

        console.print("\n[bold green]🏥 Health check completed[/bold green]")

    asyncio.run(check_health())


if __name__ == "__main__":
    # Enhanced startup with comprehensive error handling
    try:
        cli()
    except KeyboardInterrupt:
        logger.info("👋 Agent CLI interrupted by user")
        console.print("\n[yellow]👋 Agent CLI interrupted by user[/yellow]")
    except ImportError as e:
        logger.error(f"💥 Missing dependencies: {e}")
        console.print(f"\n[red]❌ Missing required dependencies:[/red] {e}")
        console.print("[yellow]💡 Try reinstalling the agent package[/yellow]")
    except Exception as e:
        logger.error(f"💥 Agent CLI failed: {e}")
        console.print(f"\n[red]❌ Agent CLI failed:[/red] {_format_error_for_user(e, 'CLI startup')}")
        console.print("[yellow]💡 Use --verbose flag for detailed error information[/yellow]")
        raise
