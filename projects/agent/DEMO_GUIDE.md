# Demo Usage Guide

This guide provides step-by-step instructions for demonstrating the Metadata Harmonization Agent in various scenarios.

## 🚀 Quick Demo Setup

### 1. Zero-Configuration Demo (Local Development)

Perfect for immediate demonstrations without any setup:

```bash
# No configuration needed - works out of the box!
cd projects/agent
pip install -e .
metadata-agent validate
```

**What happens:**
- Agent connects to `http://localhost:8080/agent/mcp` (default)
- No authentication required for local MCP servers
- Beautiful colored output with emoji indicators
- Runs validation demo with built-in test data

### CLI Command Arguments Reference

#### `metadata-agent validate` - Validate metadata files

**Basic syntax:**
```bash
metadata-agent validate [FILE_PATH] [OPTIONS]
```

**Arguments:**
- `FILE_PATH` (optional): Path to CSV file to validate. If not provided, uses built-in test data.

**Options:**
- `--interactive`: Enable interactive mode for step-by-step validation
- `--schema SCHEMA_NAME`: Specify schema to validate against (default: auto-detect)
- `--output FORMAT`: Output format (json, table, summary) - default: table
- `--verbose, -v`: Verbose output with detailed validation steps
- `--config, -c CONFIG_FILE`: Use specific configuration file

**Examples:**

```bash
# Basic validation with built-in test data
metadata-agent validate

# Validate specific file
metadata-agent validate "data/patient_metadata.csv"

# Interactive validation with specific file
metadata-agent validate "data/cyclospora_metadata.csv" --interactive

# Validate against specific schema
metadata-agent validate "data/patient_data.csv" --schema core-patient-v1.0

# Verbose validation with JSON output
metadata-agent validate "data/lab_results.csv" --verbose --output json

# Use custom configuration
metadata-agent validate "data/covid_data.csv" --config production-config.yaml --interactive

# Validate file with absolute path
metadata-agent validate "/path/to/your/metadata/file.csv" --interactive
```

#### `metadata-agent discover` - Discover available schemas

**Basic syntax:**
```bash
metadata-agent discover [OPTIONS]
```

**Options:**
- `--category CATEGORY`: Filter by schema category (core, program, specialized)
- `--format FORMAT`: Output format (tree, list, json) - default: tree
- `--include-deprecated`: Include deprecated schemas in results
- `--verbose, -v`: Show detailed schema information

**Examples:**

```bash
# Discover all schemas
metadata-agent discover

# Show only core schemas in list format
metadata-agent discover --category core --format list

# Include deprecated schemas with verbose output
metadata-agent discover --include-deprecated --verbose

# Export schema list as JSON
metadata-agent discover --format json > schemas.json
```

#### `metadata-agent interactive` - Start interactive session

**Basic syntax:**
```bash
metadata-agent interactive [OPTIONS]
```

**Options:**
- `--context FILE_PATH`: Load file context for focused conversation
- `--schema SCHEMA_NAME`: Set default schema for session
- `--config, -c CONFIG_FILE`: Use specific configuration file

**Examples:**

```bash
# Start general interactive session
metadata-agent interactive

# Interactive session with file context
metadata-agent interactive --context "data/metadata_file.csv"

# Interactive session focused on specific schema
metadata-agent interactive --schema core-patient-v1.0

# Interactive session with custom config
metadata-agent interactive --config demo-config.yaml
```

#### `metadata-agent tools` - List available MCP tools

**Basic syntax:**
```bash
metadata-agent tools [OPTIONS]
```

**Options:**
- `--format FORMAT`: Output format (table, list, json) - default: table
- `--category CATEGORY`: Filter tools by category
- `--verbose, -v`: Show detailed tool descriptions and parameters

**Examples:**

```bash
# List all available tools
metadata-agent tools

# Show tools in JSON format
metadata-agent tools --format json

# Verbose tool information
metadata-agent tools --verbose

# Filter validation tools only
metadata-agent tools --category validation
```

#### `metadata-agent query` - Execute single query

**Basic syntax:**
```bash
metadata-agent query "QUESTION" [OPTIONS]
```

**Arguments:**
- `QUESTION`: Natural language question to ask the agent

**Options:**
- `--context FILE_PATH`: Provide file context for the query
- `--schema SCHEMA_NAME`: Focus query on specific schema
- `--format FORMAT`: Response format (text, json) - default: text

**Examples:**

```bash
# Ask general question
metadata-agent query "What schemas are available for patient data?"

# Query with file context
metadata-agent query "What validation errors are in this file?" --context "data/patient_data.csv"

# Schema-specific query
metadata-agent query "What are the required fields?" --schema core-laboratory-v1.0

# Get JSON response
metadata-agent query "List all validation rules" --format json
```

### 2. Custom MCP Server Demo

For demonstrating with different MCP servers:

```bash
# Set your MCP server URL
export MCP_URL="https://your-demo-server.com/mcp"
export MCP_PAT="demo-token-if-needed"

# Run the demo
metadata-agent validate
```

### 3. Production Server Demo

For demonstrating with production-like setup:

```bash
# Production configuration
export MCP_URL="https://api.production.com/mcp"
export MCP_PAT="your-production-token"
export LOG_LEVEL="INFO"
export MCP_TIMEOUT="60"

# Run comprehensive demo
metadata-agent discover
```

## 🎯 Demo Scenarios

### Scenario 1: Validation Workflow Demo

**Purpose:** Show end-to-end metadata validation process

```bash
# Start validation demo
metadata-agent validate

# Expected output:
# 🚀 Starting Metadata Harmonization Agent
# 🔗 Connecting to http://localhost:8080/agent/mcp
# ✅ Connected successfully
# 🔧 Discovered 5 MCP tools
# 📊 Running validation demo...
# ✅ Valid metadata: patient_data_valid.csv
# ❌ Invalid metadata: patient_data_invalid.csv
# 📊 Validation completed: 3 passed, 2 failed
```

**Demo Points:**
- Zero-configuration startup
- Automatic MCP server connection
- Tool discovery process
- Validation results with visual indicators
- Error reporting with actionable feedback

### Scenario 2: Schema Discovery Demo

**Purpose:** Demonstrate schema exploration capabilities

```bash
# Start schema discovery
metadata-agent discover

# Expected output:
# 🔍 Discovering available schemas...
# 📋 Found 8 schemas:
#   ✅ core-patient-v1.0 (Patient demographics)
#   ✅ core-laboratory-v1.0 (Lab test results)
#   ✅ program-covid-v2.1 (COVID surveillance)
# 🔧 Analyzing schema relationships...
# 📊 Schema compatibility matrix generated
```

**Demo Points:**
- Comprehensive schema inventory
- Visual schema relationships
- Compatibility analysis
- Interactive exploration capabilities

### Scenario 3: Interactive Agent Demo

**Purpose:** Show conversational interface capabilities

```bash
# Start interactive session
metadata-agent interactive

# Example conversation:
# 💬 Agent: Hello! I'm your Metadata Harmonization Assistant.
# 💬 You: What schemas are available for patient data?
# 🔍 Agent: I found 3 patient-related schemas...
# 💬 You: Show me the required fields for core-patient-v1.0
# 📋 Agent: The core-patient-v1.0 schema requires...
```

**Demo Points:**
- Natural language queries
- Contextual responses
- Follow-up suggestions
- Rich formatted output

### Scenario 4: Tool Discovery Demo

**Purpose:** Demonstrate MCP tool integration

```bash
# List available tools
metadata-agent tools

# Expected output:
# 🔧 Available MCP Tools:
#
# 📊 validate_metadata
#   Description: Validate CSV metadata against schemas
#   Parameters: file_path, schema_name, validation_level
#
# 🔍 discover_schemas
#   Description: Discover and analyze available schemas
#   Parameters: category, include_deprecated
#
# 📋 get_schema_details
#   Description: Get detailed schema information
#   Parameters: schema_name, include_examples
```

**Demo Points:**
- Automatic tool discovery
- Tool documentation
- Parameter specifications
- Integration capabilities

## 🎨 Demo Presentation Tips

### 1. Terminal Setup for Presentations

**Optimal Terminal Settings:**
```bash
# Use large font for visibility
# Set terminal to at least 120x40 characters
# Use dark theme for better contrast
# Enable true color support

# Verify color support
tput colors  # Should show 256 or more

# Set optimal environment
export TERM=xterm-256color
export FORCE_COLOR=1
```

**Font and Size Recommendations:**
- **Font**: Monaco, Menlo, or Fira Code (monospace)
- **Size**: 16-20pt for presentations
- **Colors**: Dark background with bright text
- **Width**: At least 120 characters to avoid line wrapping

### 2. Demo Flow Recommendations

**Opening (2 minutes):**
1. Show zero-configuration startup
2. Demonstrate automatic connection
3. Highlight beautiful logging output

**Core Features (5 minutes):**
1. Run validation demo with visual results
2. Show schema discovery with rich output
3. Demonstrate interactive queries

**Advanced Features (3 minutes):**
1. Show tool discovery and documentation
2. Demonstrate error handling and recovery
3. Show configuration flexibility

### 3. Common Demo Scenarios

**Scenario A: "Getting Started" Demo**
```bash
# Show how easy it is to get started
cd projects/agent
pip install -e .
metadata-agent validate  # Works immediately!
```

**Scenario B: "Configuration Flexibility" Demo**
```bash
# Show different configuration methods
metadata-agent validate                    # Default config
MCP_URL="https://demo.com/mcp" metadata-agent validate  # Environment override
metadata-agent -c demo-config.yaml validate            # File config
```

**Scenario C: "Error Handling" Demo**
```bash
# Show graceful error handling
MCP_URL="http://invalid-server:9999/mcp" metadata-agent validate
# Shows: ❌ Failed to connect with helpful error message

# Show recovery
export MCP_URL="http://localhost:8080/agent/mcp"
metadata-agent validate
# Shows: ✅ Connected successfully
```

## 🔧 Environment Variable Reference

### Core Configuration

```bash
# MCP Server Configuration
export MCP_URL="http://localhost:8080/agent/mcp"     # MCP server endpoint
export MCP_PAT="your-token-here"               # Authentication token (optional for local)

# Connection Settings
export MCP_TIMEOUT="30"                        # Connection timeout (5-300 seconds)

# Logging Configuration
export LOG_LEVEL="INFO"                        # DEBUG, INFO, WARNING, ERROR

# Demo Configuration
export TEST_DATA_DIR="test_data"               # Test data directory
export FORCE_COLOR="1"                         # Force colored output
```

### Demo-Specific Settings

```bash
# Presentation Mode
export LOG_LEVEL="INFO"                        # Clean output for demos
export FORCE_COLOR="1"                         # Ensure colors in all terminals

# Development Mode
export LOG_LEVEL="DEBUG"                       # Detailed output for troubleshooting
export MCP_TIMEOUT="60"                        # Longer timeout for debugging

# Production Demo
export MCP_URL="https://api.production.com/mcp"
export MCP_PAT="production-demo-token"
export LOG_LEVEL="WARNING"                     # Minimal output for production
```

## 📊 Expected Demo Outputs

### Successful Validation Demo

```
🚀 2024-01-15 10:30:15 | INFO | Starting Metadata Harmonization Agent
🔗 2024-01-15 10:30:16 | INFO | Connecting to http://localhost:8080/agent/mcp
✅ 2024-01-15 10:30:17 | INFO | Connected successfully
🔧 2024-01-15 10:30:18 | INFO | Discovered 5 MCP tools
📊 2024-01-15 10:30:19 | INFO | Running validation demo with test data
✅ 2024-01-15 10:30:20 | INFO | Valid: patient_demographics.csv (15 records)
❌ 2024-01-15 10:30:21 | ERROR | Invalid: lab_results_bad.csv (3 errors)
   └── Missing required field: patient_id (rows 2, 5, 8)
   └── Invalid date format: collection_date (row 3)
   └── Value out of range: age (row 7: 150)
📊 2024-01-15 10:30:22 | INFO | Validation completed: 4 passed, 1 failed
👋 2024-01-15 10:30:23 | INFO | Demo completed successfully
```

### Schema Discovery Demo

```
🔍 2024-01-15 10:35:15 | INFO | Discovering available schemas
📋 2024-01-15 10:35:16 | INFO | Found 8 schemas across 3 categories:

Core Schemas:
├── 📊 core-patient-v1.0 (Patient demographics and contact info)
├── 🧪 core-laboratory-v1.0 (Laboratory test results and metadata)
└── 🏥 core-facility-v1.0 (Healthcare facility information)

Program Schemas:
├── 🦠 program-covid-v2.1 (COVID-19 surveillance data)
├── 🤧 program-flu-v1.5 (Influenza monitoring data)
└── 🔬 program-foodborne-v1.0 (Foodborne illness tracking)

Specialized Schemas:
├── 📱 mobile-app-v1.0 (Mobile application data collection)
└── 🌐 web-portal-v1.0 (Web portal data submission)

🔧 2024-01-15 10:35:18 | INFO | Analyzing schema compatibility
📊 2024-01-15 10:35:19 | INFO | Generated compatibility matrix for 28 combinations
✅ 2024-01-15 10:35:20 | INFO | Schema discovery completed
```

### Interactive Session Demo

```
💬 2024-01-15 10:40:15 | INFO | Starting interactive agent session
🤖 Agent: Hello! I'm your Metadata Harmonization Assistant.
          I can help you validate data, explore schemas, and answer questions.

          Try asking me:
          • "What schemas are available?"
          • "Validate my patient data"
          • "Show me required fields for COVID data"

💬 You: What schemas are available for patient data?

🔍 2024-01-15 10:40:30 | INFO | Searching for patient-related schemas
📋 Agent: I found 3 schemas specifically for patient data:

    1. 📊 core-patient-v1.0
       • Purpose: Basic patient demographics and contact information
       • Required fields: patient_id, first_name, last_name, date_of_birth
       • Optional fields: phone, email, address, emergency_contact

    2. 🏥 core-patient-extended-v1.0
       • Purpose: Extended patient information including medical history
       • Builds on: core-patient-v1.0
       • Additional fields: medical_record_number, insurance_info, allergies

    3. 📱 mobile-patient-v1.0
       • Purpose: Patient data collected via mobile applications
       • Simplified version of core-patient-v1.0 for mobile constraints
       • Required fields: patient_id, name, phone_or_email

    Would you like me to show you the detailed field requirements for any of these schemas?

💬 You: Show me the required fields for core-patient-v1.0

📋 Agent: Here are the required fields for core-patient-v1.0:

    🔹 patient_id (string, 1-50 chars)
      • Unique identifier for the patient
      • Pattern: alphanumeric, hyphens, underscores allowed
      • Example: "PAT-2024-001", "patient_12345"

    🔹 first_name (string, 1-100 chars)
      • Patient's first/given name
      • Pattern: letters, spaces, hyphens, apostrophes
      • Example: "John", "Mary-Jane", "José"

    🔹 last_name (string, 1-100 chars)
      • Patient's last/family name
      • Pattern: letters, spaces, hyphens, apostrophes
      • Example: "Smith", "O'Connor", "García-López"

    🔹 date_of_birth (date, ISO 8601 format)
      • Patient's birth date
      • Format: YYYY-MM-DD
      • Range: 1900-01-01 to today
      • Example: "1985-03-15", "2020-12-01"

    💡 Tip: You can validate your patient data against this schema using:
        "Please validate my CSV file against the core-patient-v1.0 schema"

💬 You: exit

👋 2024-01-15 10:42:15 | INFO | Interactive session ended
```

## 🎬 Demo Script Templates

### 5-Minute Lightning Demo

```bash
# 1. Introduction (30 seconds)
echo "Let me show you the Metadata Harmonization Agent - a simplified, demo-friendly tool for metadata validation."

# 2. Zero-config startup (1 minute)
echo "First, let's see how easy it is to get started - no configuration needed!"
metadata-agent validate

# 3. Schema discovery (2 minutes)
echo "Now let's explore what schemas are available:"
metadata-agent discover

# 4. Interactive queries (1.5 minutes)
echo "Finally, let's ask some questions interactively:"
metadata-agent query "What are the required fields for patient data?"
metadata-agent query "Show me common validation errors"

# 5. Wrap-up (30 seconds)
echo "As you can see, the agent provides beautiful output, automatic tool discovery, and natural language interaction!"
```

### 15-Minute Comprehensive Demo

```bash
# 1. Setup and introduction (2 minutes)
echo "Welcome to the Metadata Harmonization Agent demo!"
echo "This simplified agent removes complexity while maintaining full MCP functionality."

# 2. Configuration flexibility (3 minutes)
echo "Let's start with the flexible configuration system:"
echo "Default configuration (no setup needed):"
metadata-agent tools

echo "Environment variable configuration:"
export MCP_URL="http://localhost:8080/agent/mcp"
export LOG_LEVEL="DEBUG"
metadata-agent tools

echo "Configuration file:"
metadata-agent -c demo-config.yaml tools

# 3. Validation workflows (4 minutes)
echo "Now let's see the validation capabilities:"
metadata-agent validate

# 4. Schema exploration (3 minutes)
echo "Schema discovery and analysis:"
metadata-agent discover

# 5. Interactive capabilities (2 minutes)
echo "Interactive agent session:"
metadata-agent interactive
# (demonstrate a few queries)

# 6. Error handling and troubleshooting (1 minute)
echo "Error handling demonstration:"
MCP_URL="http://invalid:9999/mcp" metadata-agent validate
export MCP_URL="http://localhost:8080/agent/mcp"
metadata-agent validate
```

## 🔍 Troubleshooting During Demos

### Common Demo Issues

**Issue: Colors not showing**
```bash
# Quick fix during demo:
export FORCE_COLOR=1
export TERM=xterm-256color
```

**Issue: Connection fails**
```bash
# Quick recovery:
export MCP_URL="http://localhost:8080/agent/mcp"
unset MCP_PAT  # Remove auth for local demo
```

**Issue: Slow responses**
```bash
# Increase timeout:
export MCP_TIMEOUT="60"
```

### Demo Recovery Commands

Keep these handy during presentations:

```bash
# Reset to defaults
unset MCP_URL MCP_PAT MCP_TIMEOUT LOG_LEVEL

# Quick connection test
metadata-agent tools

# Force verbose output
metadata-agent -v validate

# Test with minimal config
LOG_LEVEL=INFO metadata-agent validate
```

This guide should help you deliver smooth, impressive demonstrations of the Metadata Harmonization Agent's capabilities!
