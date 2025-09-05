# Standardize App Interface Architecture

## Current State

### CMD Apps
- **proxy mode**: Pass all arguments directly to command
- **curated mode**: Use argparse with defined parameters

### MCP Apps
- No mode distinction
- Always fetches tool definitions from server
- Builds dynamic argparse based on fetched schema

## Proposed Architecture

### Unified Mode System for Both CMD and MCP

#### 1. **Proxy Mode** (pass-through)
- **CMD**: Pass all args directly to command (current behavior)
- **MCP**: Pass all args directly to tool without validation
- Use case: Quick and dirty, trust the user knows what they're doing

#### 2. **Curated Mode** (structured)
- **CMD**: Use predefined argparse (current behavior)
- **MCP**: Use cached/predefined tool schemas for validation
- Use case: Production usage with proper validation and help

#### 3. **Dynamic Mode** (MCP only, current default)
- Fetch tool definitions from server
- Build argparse dynamically
- Use case: Development, exploring new servers

## Schema Caching System

### Storage Format
```yaml
# ~/.tasak/schemas/<app_name>.yaml
app: gok
last_updated: 2024-01-20T10:00:00Z
transport: sse
tools:
  health_check:
    description: "Check if GOK MCP server is healthy"
    input_schema:
      type: object
      properties: {}
      required: []

  note_create:
    description: "Create structured knowledge base entry"
    input_schema:
      type: object
      properties:
        title:
          type: string
          description: "Note title"
        content:
          type: string
          description: "Note content"
      required: ["title", "content"]
```

### Benefits
1. **Performance**: No need to fetch schemas every time
2. **Offline capability**: Can use tools without server connection
3. **Version control**: Can track schema changes
4. **Documentation**: YAML files serve as documentation

## Admin Commands Restructure

### Current
```bash
tasak auth <app>           # Authentication
tasak <app> --clear-cache  # Clear cache
```

### Proposed
```bash
tasak admin auth <app>      # Manage authentication
tasak admin refresh <app>   # Refresh tool schemas from server
tasak admin clear <app>     # Clear all app data (auth, cache, schemas)
tasak admin list            # List all configured apps with status
tasak admin info <app>      # Show app details (auth status, schema age, etc.)
```

## Implementation Steps

### Phase 1: Admin Command Structure
1. Create `admin_commands.py` module
2. Move auth functionality to `tasak admin auth`
3. Implement `tasak admin refresh` for schema updates
4. Implement `tasak admin info` for app status

### Phase 2: Schema Management
1. Create `schema_manager.py` for loading/saving schemas
2. Implement YAML schema storage
3. Add schema versioning and timestamps
4. Create migration for existing cache to new format

### Phase 3: Unified Mode System
1. Add `mode` parameter to app configs:
   ```yaml
   gok:
     type: mcp
     mode: curated  # or proxy, dynamic
     schema: ~/.tasak/schemas/gok.yaml
   ```
2. Implement proxy mode for MCP (no validation)
3. Implement curated mode for MCP (use cached schemas)
4. Keep dynamic mode as fallback

### Phase 4: Argument Filtering
Based on mode:
- **proxy**: Pass everything except TASAK flags
- **curated**: Only pass arguments defined in schema
- **dynamic**: Filter based on fetched schema

## Benefits
1. **Consistency**: Same mode concept for both CMD and MCP
2. **Performance**: Cached schemas = faster startup
3. **Reliability**: Can work offline with cached schemas
4. **Flexibility**: Choose validation level per use case
5. **Maintainability**: Clear separation of concerns

## Migration Path
1. Keep current behavior as default
2. Gradually migrate apps to use modes
3. Provide `tasak admin migrate` to convert old cache
