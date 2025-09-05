# Admin Auth & Refresh Implementation

## Priority 1: Core Admin Commands

### `tasak admin auth <app>`

#### Purpose
Centralized authentication management for all app types.

#### Subcommands
```bash
tasak admin auth <app>           # Interactive auth flow
tasak admin auth <app> --check   # Check auth status
tasak admin auth <app> --clear   # Remove stored credentials
tasak admin auth <app> --refresh # Refresh expired tokens
```

#### Implementation
1. Move current `tasak auth` logic to admin module
2. Support different auth types:
   - OAuth 2.0 (Atlassian, GitHub)
   - API keys (future)
   - No auth (local servers like GOK)

#### Storage
- Keep using `~/.tasak/auth.json` for credentials
- Add metadata:
  ```json
  {
    "atlassian": {
      "access_token": "...",
      "refresh_token": "...",
      "expires_at": 1234567890,
      "auth_type": "oauth2",
      "last_refresh": "2024-01-20T10:00:00Z"
    },
    "gok": {
      "auth_type": "none",
      "note": "Local server, no auth required"
    }
  }
  ```

### `tasak admin refresh <app>`

#### Purpose
Update cached tool schemas from MCP servers.

#### Behavior
```bash
tasak admin refresh <app>        # Refresh specific app
tasak admin refresh --all        # Refresh all apps
tasak admin refresh <app> --force # Ignore cache age, force refresh
```

#### Process
1. Connect to MCP server
2. Fetch tool definitions
3. Save to `~/.tasak/schemas/<app>.yaml`
4. Include metadata:
   ```yaml
   # ~/.tasak/schemas/gok.yaml
   version: 1.0
   app: gok
   fetched_at: 2024-01-20T10:00:00Z
   server_version: "2.1.0"  # if available
   transport: sse
   url: http://localhost:7870/sse

   tools:
     health_check:
       description: "Check server health"
       input_schema:
         type: object
         properties: {}

     note_create:
       description: "Create note"
       input_schema:
         type: object
         properties:
           title:
             type: string
             description: "Note title"
           content:
             type: string
         required: ["title", "content"]
   ```

#### Benefits
- Work offline with cached schemas
- Faster startup (no fetch needed)
- Track schema changes over time
- Documentation in readable format

### Admin Module Structure

```python
# tasak/admin/__init__.py
# tasak/admin/auth.py
# tasak/admin/refresh.py
# tasak/admin/info.py
```

### CLI Integration

```python
# main.py modifications
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # Admin subcommand
    admin_parser = subparsers.add_parser('admin', help='Administrative commands')
    admin_subparsers = admin_parser.add_subparsers()

    # Auth subcommand
    auth_parser = admin_subparsers.add_parser('auth', help='Manage authentication')
    auth_parser.add_argument('app', help='Application name')
    auth_parser.add_argument('--check', action='store_true')
    auth_parser.add_argument('--clear', action='store_true')
    auth_parser.add_argument('--refresh', action='store_true')

    # Refresh subcommand
    refresh_parser = admin_subparsers.add_parser('refresh', help='Refresh tool schemas')
    refresh_parser.add_argument('app', nargs='?', help='Application name')
    refresh_parser.add_argument('--all', action='store_true')
    refresh_parser.add_argument('--force', action='store_true')
```

## Implementation Priority

### Step 1: Create admin module structure
- Create `tasak/admin/` directory
- Move existing auth logic

### Step 2: Implement `admin auth`
- Migrate from current `tasak auth`
- Add --check, --clear, --refresh flags
- Maintain backward compatibility temporarily

### Step 3: Implement `admin refresh`
- Create schema fetching logic
- YAML storage format
- Metadata tracking

### Step 4: Update app runners
- Check for cached schemas first
- Fall back to dynamic fetch
- Use schemas for argument validation

## Auto-fetch Behavior

### First Run Experience
When user runs `tasak <app>` for the first time:

1. **Check for schema file**
   ```python
   schema_path = Path.home() / ".tasak" / "schemas" / f"{app_name}.yaml"
   if not schema_path.exists():
       print(f"First run detected. Fetching tool definitions for '{app_name}'...")
       fetch_and_save_schema(app_name)
   ```

2. **Auto-refresh if stale**
   ```python
   if is_schema_stale(schema_path, max_age_days=7):
       print(f"Schema is {days_old} days old. Refreshing...")
       fetch_and_save_schema(app_name)
   ```

3. **Simple logic**
   ```python
   schema_path = Path.home() / ".tasak" / "schemas" / f"{app_name}.yaml"

   # Try to load cached schema
   if schema_path.exists():
       schema = load_schema_from_yaml(schema_path)
       # Optional: warn if old
       age_days = get_schema_age(schema_path)
       if age_days > 30:
           print(f"Note: Schema is {age_days} days old. Consider 'tasak admin refresh {app_name}'")
   else:
       # First run - must fetch
       print(f"First run detected. Fetching tool definitions for '{app_name}'...")
       try:
           schema = fetch_and_save_schema(app_name)
       except ConnectionError:
           print(f"Cannot connect to {app_name} server. Is it running?")
           sys.exit(1)
   ```

### Schema Lifecycle

```
First run → Auto-fetch → Save to YAML
     ↓
Daily use → Use cached (fast!)
     ↓
30+ days old → Suggestion to refresh
     ↓
Manual refresh → tasak admin refresh <app>
```

### User Messages

#### First run:
```
$ tasak gok --help
→ First time using 'gok'. Fetching tool definitions...
→ Successfully cached 28 tools for offline use.
→ (Use 'tasak admin refresh gok' to update manually)
[shows help]
```

#### Stale schema:
```
$ tasak gok note_create
→ Note: Schema is 15 days old. Run 'tasak admin refresh gok' to update.
[continues with cached schema]
```

#### Server unreachable (first run):
```
$ tasak gok note_create
→ First run detected. Fetching tool definitions for 'gok'...
→ Error: Cannot connect to gok server. Is it running?
[exits]
```

#### Server unreachable (has cache):
```
$ tasak gok note_create
[uses cached schema, executes command]
→ Error: Cannot connect to gok server at http://localhost:7870/sse
[exits - because can't actually execute without server]
```

## Success Criteria
1. `tasak admin auth atlassian` triggers OAuth flow
2. `tasak admin refresh gok` saves tools to YAML
3. `tasak gok` uses cached schema (faster startup)
4. `tasak admin auth gok --check` shows "no auth required"

## Future Extensions
- `tasak admin info <app>` - show status, schema age, etc.
- `tasak admin clear <app>` - remove all app data
- `tasak admin export <app>` - export config for sharing
- `tasak admin import <file>` - import shared config
