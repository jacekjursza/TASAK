# Admin Command Improvements

## Current State

The admin interface exists (`tasak admin`) with basic commands:
- `auth` - Manage authentication
- `refresh` - Refresh tool schemas
- `clear` - Clear app data
- `info` - Show app information
- `list` - List all apps with status

## Problems

1. **Pool Management Missing** - No commands to manage the new process pool
2. **Debug Visibility** - No way to debug what's happening inside TASAK
3. **Schema Management** - Limited schema operations (no export, import, validate)
4. **Diagnostics** - No health checks or troubleshooting tools
5. **Configuration** - No commands to manage config files

## Proposed Improvements

### 1. Process Pool Management

```bash
# View pool status
tasak admin pool status
# Output:
# Process Pool Status:
#   Active processes: 2/10
#   Total connections: 47
#   Uptime: 2h 15m
#
# Processes:
#   atlassian    - alive (idle: 30s)
#   github       - alive (idle: 5m)

# Clear specific process
tasak admin pool kill atlassian

# Clear all processes
tasak admin pool clear

# Adjust pool settings
tasak admin pool config --idle-timeout 600 --max-size 20
```

### 2. Debug and Diagnostics

```bash
# Enable debug mode for a command
tasak admin debug atlassian list --verbose
# Shows: Request/response, timing, process info

# Run diagnostics
tasak admin diagnose atlassian
# Checks: Auth status, connectivity, schema validity, process health

# View logs
tasak admin logs --tail 50
tasak admin logs atlassian --since "10m ago"

# Test connectivity
tasak admin test atlassian
# Runs: Auth check, list tools, simple tool call
```

### 3. Schema Management

```bash
# Export schema
tasak admin schema export atlassian > atlassian-schema.json

# Import schema
tasak admin schema import atlassian < custom-schema.json

# Validate schema
tasak admin schema validate atlassian

# Compare schemas
tasak admin schema diff atlassian github

# Generate documentation from schema
tasak admin schema docs atlassian --format markdown
```

### 4. Configuration Management

```bash
# Show effective config (merged)
tasak admin config show

# Validate config files
tasak admin config validate

# Edit config with validation
tasak admin config edit --global
tasak admin config edit --local

# Add new app interactively
tasak admin config add-app
# Interactive wizard for app configuration

# Export/import configs
tasak admin config export > backup.yaml
tasak admin config import < backup.yaml
```

### 5. Stats and Monitoring

```bash
# Show usage statistics
tasak admin stats
# Output:
# TASAK Statistics:
#   Total commands: 1,234
#   Success rate: 98.5%
#   Average latency: 150ms
#   Most used: atlassian (45%), github (30%)
#   Cache hit rate: 75%

# Monitor in real-time
tasak admin monitor
# Live dashboard showing current activity

# Performance analysis
tasak admin perf atlassian
# Shows: Startup time, auth time, execution time breakdown
```

### 6. Batch Operations

```bash
# Refresh all schemas
tasak admin refresh --all

# Clear everything for an app
tasak admin reset atlassian

# Backup all TASAK data
tasak admin backup ~/.tasak-backup

# Restore from backup
tasak admin restore ~/.tasak-backup
```

## Implementation Plan

### Phase 1: Pool Management (Priority: HIGH)
Add pool commands to manage the new MCPRemotePool:
- `pool status` - Show current pool state
- `pool kill <app>` - Terminate specific process
- `pool clear` - Clear all processes
- `pool config` - Adjust pool settings

**Files to modify:**
- `admin_commands.py` - Add pool subcommands
- `mcp_remote_pool.py` - Add management methods

### Phase 2: Debug Tools (Priority: HIGH)
Add debugging capabilities:
- `debug <app> <command>` - Run with verbose output
- `diagnose <app>` - Health check
- `test <app>` - Connectivity test

**Files to modify:**
- `admin_commands.py` - Add debug subcommands
- Create `debug_utils.py` - Debug helpers

### Phase 3: Schema Tools (Priority: MEDIUM)
Enhance schema management:
- `schema export/import` - Backup/restore schemas
- `schema validate` - Check schema integrity
- `schema docs` - Generate documentation

**Files to modify:**
- `admin_commands.py` - Add schema subcommands
- `schema_manager.py` - Add export/import methods

### Phase 4: Config Management (Priority: MEDIUM)
Add configuration tools:
- `config show` - Display merged config
- `config validate` - Check config syntax
- `config add-app` - Interactive app setup

**Files to modify:**
- `admin_commands.py` - Add config subcommands
- `config.py` - Add validation methods

### Phase 5: Monitoring (Priority: LOW)
Add monitoring and stats:
- `stats` - Usage statistics
- `monitor` - Live monitoring
- `perf` - Performance analysis

**Files to modify:**
- `admin_commands.py` - Add monitoring subcommands
- Create `stats_collector.py` - Statistics tracking

## Benefits

1. **Better Debugging** - Quickly diagnose issues
2. **Pool Visibility** - Understand process reuse
3. **Schema Control** - Manage tool definitions
4. **Config Safety** - Validate before breaking
5. **Performance Insights** - Optimize usage

## Example Use Cases

### Troubleshooting Slow Commands
```bash
# Check pool status
tasak admin pool status
# See: atlassian process dead

# Diagnose the issue
tasak admin diagnose atlassian
# Error: OAuth token expired

# Fix and test
tasak admin auth atlassian
tasak admin test atlassian
# Success!
```

### Setting Up New Environment
```bash
# Export from dev machine
tasak admin config export > tasak-config.yaml
tasak admin schema export --all > schemas.json

# Import on new machine
tasak admin config import < tasak-config.yaml
tasak admin schema import --all < schemas.json

# Verify setup
tasak admin diagnose --all
```

### Performance Optimization
```bash
# Check current performance
tasak admin perf atlassian
# Shows: 3s startup time

# Adjust pool settings
tasak admin pool config --idle-timeout 900

# Monitor improvement
tasak admin monitor
# Observe: Subsequent calls now <500ms
```

## Success Metrics

- Reduce troubleshooting time by 80%
- Enable self-service debugging
- Provide visibility into process pool
- Simplify configuration management
- Enable performance optimization

## Estimated Effort

- Phase 1 (Pool): 4 hours
- Phase 2 (Debug): 6 hours
- Phase 3 (Schema): 4 hours
- Phase 4 (Config): 6 hours
- Phase 5 (Monitor): 8 hours
- **Total: ~3.5 days**

## Priority

**HIGH** - These tools are essential for:
1. Understanding the new process pool behavior
2. Debugging production issues
3. Managing complex configurations
4. Optimizing performance
