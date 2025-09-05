# Fix Argument Passing to MCP Tools

## Problem
When calling MCP tools, TASAK passes ALL parsed arguments (except `tool_name`) to the tool.
This includes TASAK-specific flags like `--clear-cache` which causes validation errors.

## Error Example
```
Error calling tool 'health_check': 1 validation error for call[health_check]
clear_cache
  Unexpected keyword argument
```

## Root Cause
Line 41 in mcp_client.py:
```python
tool_args = {k: v for k, v in vars(parsed_args).items() if k != "tool_name"}
```

This includes:
- `clear_cache` (from --clear-cache flag)
- Any other TASAK-specific arguments

## Quick Fix (Before 003)
Minimal fix - just filter known TASAK flags:
```python
# In mcp_client.py line 41
TASAK_FLAGS = {'clear_cache'}  # Add more as needed
tool_args = {k: v for k, v in vars(parsed_args).items()
             if k != "tool_name" and k not in TASAK_FLAGS}
```

## Proper Solution (Task 003)
This will be properly solved by implementing curated mode in task 003-standardize-app-interface,
where we only pass arguments defined in the tool's schema.

## Decision: SKIP THIS TASK
Since 003 will solve this properly, we can either:
1. Apply quick fix above (5 minutes) if blocking
2. Skip and go straight to 003

**Recommendation: Skip 001, implement 003 directly**
