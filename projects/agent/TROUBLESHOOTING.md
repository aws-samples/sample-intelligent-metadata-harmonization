# Troubleshooting Guide

This guide provides comprehensive solutions for common issues with the Metadata Harmonization Agent.

## 🚀 Quick Diagnostics

Before diving into specific issues, run these quick diagnostic commands:

```bash
# Test basic functionality
metadata-agent tools

# Check configuration
metadata-agent -v query "test connection"

# Verify environment variables
env | grep MCP

# Test with minimal configuration
unset MCP_URL MCP_PAT MCP_TIMEOUT LOG_LEVEL
metadata-agent validate <metadata_file.csv>
```

## 🔧 Common Issues & Solutions

### 1. Connection Problems

#### Issue: "Connection refused" or "Failed to connect"
```
❌ Error: Failed to connect to http://localhost:8080/agent/mcp: Connection refused
```

**Causes & Solutions:**

**🔍 MCP Server Not Running**
```bash
# Check if server is running
curl http://localhost:8080/agent/mcp
# or
curl -I http://localhost:8080/health

# If not running, start your MCP server
# (specific commands depend on your server setup)
```

**🔍 Wrong URL or Port**
```bash
# Check correct URL format
export MCP_URL="http://localhost:8080/agent/mcp"  # Include protocol and path

# Common variations to try:
export MCP_URL="http://localhost:3000/agent/mcp"
export MCP_URL="https://your-server.com/mcp"
```

**🔍 Network/Firewall Issues**
```bash
# Test network connectivity
ping localhost
telnet localhost 8080

# Check firewall settings (macOS)
sudo pfctl -sr | grep 8080

# Check firewall settings (Linux)
sudo iptables -L | grep 8080
```

#### Issue: "Timeout" errors
```
❌ Error: Connection timeout after 30 seconds
```

**Solutions:**
```bash
# Increase timeout for slow connections
export MCP_TIMEOUT="60"

# Or use configuration file
echo "timeout: 60" >> config.yaml

# Test with longer timeout
MCP_TIMEOUT=120 metadata-agent validate <metadata_file.csv>
```

### 2. Authentication Issues

#### Issue: "Unauthorized" or "Invalid token"
```
❌ Error: 401 Unauthorized
❌ Error: Invalid MCP_PAT token format
```

**Solutions:**

**🔍 Local Development (No Auth Required)**
```bash
# For local MCP servers, no token needed
unset MCP_PAT
export MCP_URL="http://localhost:8080/agent/mcp"
metadata-agent validate <metadata_file.csv>
```

**🔍 Production Servers (Auth Required)**
```bash
# Set valid personal access token
export MCP_PAT="your-valid-bearer-token"

# Verify token format (should be alphanumeric string)
echo $MCP_PAT | wc -c  # Should be reasonable length (20-100 chars)

# Test token validity
curl -H "Authorization: Bearer $MCP_PAT" $MCP_URL
```

**🔍 Token Refresh**
```bash
# If token expired, get new one from your MCP server admin
# Then update environment variable
export MCP_PAT="new-token-here"
```

### 3. Configuration Errors

#### Issue: Invalid configuration values
```
❌ Error: Invalid URL format: localhost:8080
❌ Error: Invalid timeout value: -5
❌ Error: Invalid log level: VERBOSE
```

**Solutions:**

**🔍 URL Format Issues**
```bash
# ❌ Wrong formats:
# localhost:8080
# 8080/agent/mcp
# ftp://localhost:8080/agent/mcp

# ✅ Correct formats:
export MCP_URL="http://localhost:8080/agent/mcp"
export MCP_URL="https://api.example.com/mcp"
```

**🔍 Timeout Range Issues**
```bash
# ❌ Invalid timeouts:
# MCP_TIMEOUT=-5    (negative)
# MCP_TIMEOUT=0     (zero)
# MCP_TIMEOUT=1000  (too large)

# ✅ Valid timeouts (5-300 seconds):
export MCP_TIMEOUT="30"   # Default
export MCP_TIMEOUT="60"   # For slower connections
export MCP_TIMEOUT="120"  # For very slow connections
```

**🔍 Log Level Issues**
```bash
# ❌ Invalid log levels:
# LOG_LEVEL=VERBOSE
# LOG_LEVEL=TRACE
# LOG_LEVEL=1

# ✅ Valid log levels:
export LOG_LEVEL="DEBUG"    # Most verbose
export LOG_LEVEL="INFO"     # Default
export LOG_LEVEL="WARNING"  # Warnings only
export LOG_LEVEL="ERROR"    # Errors only
```

#### Issue: Configuration file problems
```
❌ Error: YAML syntax error in config.yaml line 5
❌ Error: Configuration file not found
```

**Solutions:**

**🔍 YAML Syntax Errors**
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Common YAML issues:
# - Missing quotes around URLs with special characters
# - Incorrect indentation (use spaces, not tabs)
# - Missing colons after keys

# Example correct format:
cat > config.yaml << EOF
mcp_url: "http://localhost:8080/agent/mcp"
timeout: 30
log_level: "INFO"
test_data_dir: "test_data"
EOF
```

**🔍 Missing Configuration File**
```bash
# Agent works without config file (uses environment variables)
# But if you want one, create it:
cp config.yaml.example config.yaml

# Or use environment variables instead:
export MCP_URL="http://localhost:8080/agent/mcp"
export LOG_LEVEL="INFO"
```

### 4. Installation & Dependency Issues

#### Issue: Import errors or missing modules
```
❌ Error: ModuleNotFoundError: No module named 'loguru'
❌ Error: ModuleNotFoundError: No module named 'metadata_agent'
```

**Solutions:**

**🔍 Missing Dependencies**
```bash
# Reinstall with all dependencies
pip install -e .

# Or install development dependencies
pip install -e ".[dev]"

# Install specific missing modules
pip install loguru rich click

# Check installed packages
pip list | grep -E "(loguru|rich|click|mcp|strands)"
```

**🔍 Python Version Issues**
```bash
# Check Python version (need 3.9+)
python --version

# If using wrong version, use specific Python
python3.9 -m pip install -e .
python3.10 -m pip install -e .

# Or use virtual environment with correct version
python3.9 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**🔍 Package Installation Issues**
```bash
# Clear pip cache and reinstall
pip cache purge
pip uninstall metadata-harmonization-agent
pip install -e .

# Check for conflicting packages
pip check

# Install in clean environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install -e .
```

#### Issue: Permission errors during installation
```
❌ Error: Permission denied: '/usr/local/lib/python3.9/site-packages/'
```

**Solutions:**
```bash
# Use user installation
pip install --user -e .

# Or use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate
pip install -e .

# On macOS with Homebrew Python
/opt/homebrew/bin/python3 -m pip install -e .
```

### 5. Tool Discovery & MCP Issues

#### Issue: "No tools available" or empty tool list
```
❌ Error: No MCP tools discovered
❌ Error: Tool discovery failed
```

**Solutions:**

**🔍 MCP Server Tool Registration**
```bash
# Check if MCP server has tools registered
curl $MCP_URL/tools 2>/dev/null | jq .

# Or use agent to list tools
metadata-agent tools

# Enable debug logging to see discovery process
LOG_LEVEL=DEBUG metadata-agent tools
```

**🔍 MCP Server Configuration**
```bash
# Verify MCP server is properly configured
# Check server logs for tool registration messages
# Ensure server has metadata harmonization tools loaded

# Test basic MCP connectivity
metadata-agent query "hello"
```

**🔍 Network/Protocol Issues**
```bash
# Test raw MCP connection
curl -X POST $MCP_URL \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'

# Check for protocol version mismatches in server logs
```

#### Issue: Tool execution failures
```
❌ Error: Tool 'validate_metadata' execution failed
❌ Error: Invalid tool arguments
```

**Solutions:**

**🔍 Tool Argument Issues**
```bash
# Enable debug logging to see exact arguments sent
LOG_LEVEL=DEBUG metadata-agent validate <metadata_file.csv>

# Check tool documentation
metadata-agent tools  # Lists available tools and their parameters

# Test with minimal arguments
metadata-agent query "list available tools"
```

**🔍 Server-Side Tool Errors**
```bash
# Check MCP server logs for detailed error messages
# Common issues:
# - Missing required parameters
# - Invalid data formats
# - Server-side processing errors

# Test with a different file
metadata-agent validate <different_metadata_file.csv>
```

### 6. Demo & Presentation Issues

#### Issue: Logging output not colorful or formatted
```
❌ Issue: Plain text output without colors or emoji
```

**Solutions:**

**🔍 Terminal Compatibility**
```bash
# Check terminal color support
echo $TERM
tput colors

# Force color output
export FORCE_COLOR=1
metadata-agent validate <metadata_file.csv>

# Use rich terminal if available
export TERM=xterm-256color
```

**🔍 Loguru Configuration**
```bash
# Enable colorized output explicitly
LOG_LEVEL=INFO metadata-agent -v validate <metadata_file.csv>

# Check if running in non-interactive environment
# (colors disabled in pipes/redirects)
metadata-agent validate <metadata_file.csv> | cat  # No colors (expected)
metadata-agent validate <metadata_file.csv>        # Colors (expected)
```

#### Issue: Demo data not found
```
❌ Error: Test data directory not found: test_data
❌ Error: No valid test files found
```

**Solutions:**

**🔍 Test Data Setup**
```bash
# Check if test data exists
ls -la test_data/

# If missing, create basic test data structure
mkdir -p test_data/{valid,invalid,edge_cases,corrections}

# Copy example data if available
cp -r examples/test_data/* test_data/ 2>/dev/null || true

# Or specify custom test data directory
export TEST_DATA_DIR="/path/to/your/test/data"
```

**🔍 File Permissions**
```bash
# Check file permissions
ls -la test_data/
chmod -R 644 test_data/*.csv test_data/*.json
chmod 755 test_data/
```

## 🔍 Advanced Debugging

### Enable Maximum Verbosity

```bash
# Full debug output with backtraces
LOG_LEVEL=DEBUG metadata-agent -v interactive

# Trace MCP communication
export MCP_DEBUG=1
LOG_LEVEL=DEBUG metadata-agent -v tools
```

### Network Debugging

```bash
# Monitor network traffic (macOS)
sudo tcpdump -i lo0 port 8080

# Monitor network traffic (Linux)
sudo tcpdump -i lo port 8080

# Use netstat to check connections
netstat -an | grep 8080
```

### Configuration Debugging

```bash
# Show effective configuration
metadata-agent -v query "show config" 2>&1 | grep -E "(config|MCP_|LOG_)"

# Test configuration loading
python -c "
from metadata_agent.config import AgentConfig
config = AgentConfig.from_env()
print(f'URL: {config.mcp_url}')
print(f'Timeout: {config.timeout}')
print(f'Log Level: {config.log_level}')
"
```

## 🆘 Getting Help

### Information to Collect

When reporting issues, please include:

1. **Environment Information:**
   ```bash
   python --version
   pip list | grep -E "(metadata|loguru|rich|mcp|strands)"
   env | grep MCP
   ```

2. **Error Messages:**
   ```bash
   # Run with full debug output
   LOG_LEVEL=DEBUG metadata-agent -v [command] 2>&1 | tee debug.log
   ```

3. **Configuration:**
   ```bash
   # Sanitized configuration (remove sensitive tokens)
   cat config.yaml 2>/dev/null || echo "No config file"
   env | grep -E "^(MCP_|LOG_)" | sed 's/PAT=.*/PAT=***/'
   ```

4. **Network Connectivity:**
   ```bash
   curl -I $MCP_URL 2>&1
   ```

### Support Channels

1. 📋 **Create an Issue**: Include debug logs and environment info
2. 📖 **Check Documentation**: Review README and configuration sections
3. 🧪 **Test Minimal Setup**: Try with default configuration
4. 🔍 **Search Existing Issues**: Look for similar problems and solutions

### Quick Reset

If all else fails, try a complete reset:

```bash
# 1. Clean environment
unset MCP_URL MCP_PAT MCP_TIMEOUT LOG_LEVEL

# 2. Reinstall in clean environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install -e .

# 3. Test with defaults
metadata-agent validate <metadata_file.csv>

# 4. If working, gradually add your configuration back
export MCP_URL="your-url-here"
metadata-agent validate <metadata_file.csv>
```

This should resolve most configuration and environment-related issues.
