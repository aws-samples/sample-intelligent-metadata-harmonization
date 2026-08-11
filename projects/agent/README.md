# Agent - AI Assistant for Metadata Operations

Conversational AI agent for natural language interaction with metadata validation and schema management through MCP (Model Context Protocol).

## Quick Start

Prerequisites: API must be running with MCP server enabled (see `../api/README.md`)

```bash
# Start API first (required dependency)
cd projects/api && make runApiLocal  # Terminal 1

# Install and run agent demos
cd projects/agent
pip install -e .
metadata-agent validate ../../data/synthetic_dataset/simple_test.csv  # Terminal 2: Validate a metadata file
metadata-agent discover        # Schema exploration demo
metadata-agent interactive     # Conversational interface
```

## Architecture

This agent is a lightweight MCP client that communicates with the Metadata Harmonization API server through the Model Context Protocol. It uses AWS Strands MCPClient with streamable HTTP transport and Claude Sonnet 4 for natural language processing. The agent maintains no local state; all processing happens on the API server.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_URL` | `http://localhost:8080/agent/mcp` | API MCP endpoint |
| `MCP_PAT` | None | Personal access token (production only) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MCP_TIMEOUT` | `30` | Connection timeout in seconds (5-300) |

## CLI Commands

| Command | Description |
|---------|-------------|
| `metadata-agent validate <file>` | Validate a metadata file against a schema (file path required) |
| `metadata-agent discover` | Explore available schemas |
| `metadata-agent interactive` | Start conversational interface |
| `metadata-agent query "text"` | Ask a single question |
| `metadata-agent tools` | List available MCP tools |
| `metadata-agent -c config.yaml <cmd>` | Use custom configuration file |
| `metadata-agent -v <cmd>` | Enable debug logging |

## Project Structure

```
projects/agent/
├── src/
│   └── metadata_agent/
│       ├── main.py                  # CLI entry point and AWS Strands agent
│       ├── base_client.py           # Abstract base class for MCP clients
│       ├── streamable_http_client.py # StreamableHTTPMCPClient implementation
│       ├── config.py                # Configuration management
│       ├── examples/                # Demo scripts
│       │   ├── validation_demo.py   # Validation workflow demo
│       │   ├── schema_discovery.py  # Schema exploration demo
│       │   └── interactive_agent.py # Interactive CLI demo
│       └── utils/
│           └── logging_config.py    # Loguru-based logging
├── test_data/                       # Sample datasets
│   ├── valid/                       # Valid metadata samples
│   ├── invalid/                     # Invalid metadata samples
│   ├── edge_cases/                  # Edge case samples
│   └── corrections/                 # Before/after correction examples
├── tests/                           # Test suite
├── config.yaml.example             # Example configuration
├── pyproject.toml                   # Project configuration
└── README.md                        # This file
```

## Configuration File (Optional)

Create `config.yaml` for persistent settings:

```yaml
mcp_url: "http://localhost:8080/agent/mcp"
timeout: 30
log_level: "INFO"
test_data_dir: "test_data"
```

Configuration priority: Environment variables > YAML file > Built-in defaults

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=metadata_agent

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## Python API Usage

```python
from metadata_agent.main import MetadataAgent
from metadata_agent.config import AgentConfig

# Initialize agent with environment-based configuration
config = AgentConfig.from_env()
agent = MetadataAgent(config)

# Connect to MCP server and discover tools
await agent.initialize()

# Execute natural language queries
response = await agent.execute_query(
    "Please validate this CSV metadata using the patient-data schema"
)

# Clean shutdown
await agent.shutdown()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Verify MCP server is running: `curl http://localhost:8080/agent/mcp` |
| Invalid URL format | Ensure URL starts with `http://` or `https://` |
| Missing dependencies | Reinstall: `pip install -e .` |
| No tools discovered | Check server logs, verify with `metadata-agent tools` |
| Authentication errors | For local dev, no `MCP_PAT` needed; for production, set valid token |

Enable debug mode for detailed troubleshooting:
```bash
metadata-agent -v interactive
LOG_LEVEL=DEBUG metadata-agent validate <metadata_file.csv>
```
