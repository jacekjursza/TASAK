# Task 004: MCP Client Proxy

**Objective:** Implement a dynamic command-line client proxy for MCP servers, allowing TASAK to expose tools from any MCP server as native CLI sub-commands.

**MVP Scope:** For the initial implementation, this proxy will only support connecting to already running **SSE (Server-Sent Events)** servers.

---

## 1. Configuration

The `tasak.yaml` configuration for an MCP app will be simple:

```yaml
atlassian:
  type: "mcp"
  # Path to the MCP connection configuration file.
  config: "~/.mcp/configs/atlassian.json"
```

The referenced JSON file will contain the server connection details. For the MVP, it only needs to support SSE:

```json
# ~/.mcp/configs/atlassian.json
{
  "transport": "sse",
  "url": "https://mcp.atlassian.com/v1/sse",
  "headers": {
    "Authorization": "Bearer ${ATLASSIAN_API_KEY}"
  }
}
```

**Requirements:**
*   Implement logic to read the `tasak.yaml` file for an app of `type: "mcp"`.
*   Read the JSON file specified in the `config` path.
*   The JSON parser must support environment variable substitution (e.g., `${ATLASSIAN_API_KEY}`).

---

## 2. Dynamic CLI Generation

This is the core of the task. When a user runs `tasak <app_name> ...`, TASAK must dynamically build a CLI interface.

**Requirements:**

1.  **Tool Discovery:**
    *   On first run, connect to the MCP server using the details from the JSON config (using the `mcp` Python SDK, specifically `sse_client`).
    *   Call `session.list_tools()` to get a list of all available tools.

2.  **Tool Definition Caching:**
    *   To ensure performance, the result of `list_tools()` **must be cached** locally (e.g., in `~/.tasak/cache/<app_name>.json`).
    *   Implement a cache invalidation strategy (e.g., cache expires after 15 minutes, or can be manually cleared with a command like `tasak <app_name> --clear-cache`).

3.  **Dynamic Parser Building:**
    *   Using the cached tool definitions, dynamically build a CLI parser (e.g., with `argparse` or `click`).
    *   The main app (`tasak atlassian`) should have sub-commands for each tool discovered (`create_ticket`, `list_projects`).
    *   The arguments for each sub-command must be generated from the tool's `input_schema`.
    *   The `description` of the tool should be used as the help text for the sub-command.

---

## 3. Tool Execution

When a user executes a full command, TASAK must call the corresponding MCP tool.

**Requirements:**

1.  **Argument Parsing:**
    *   Use the dynamically generated parser to parse the command-line arguments.

2.  **MCP Tool Call:**
    *   Connect to the MCP server.
    *   Call the specified tool using `session.call_tool(<tool_name>, <parsed_arguments_dict>)`.

3.  **Output Handling:**
    *   Take the `content` from the `call_tool` response.
    *   Print the result to standard output in a clean, human-readable format. If the result is JSON, it should be pretty-printed.

---

## Acceptance Criteria

*   Running `tasak atlassian --help` connects to the server (or uses cache), discovers tools, and displays them as available sub-commands.
*   Running `tasak atlassian create_ticket --help` displays help for that specific tool, generated from its `input_schema` and `description`.
*   Running `tasak atlassian create_ticket --project "PROJ"` successfully calls the `create_ticket` tool on the remote MCP server with the correct parameters.
*   The result of the tool call is printed to the console.
*   Tool definitions are cached to avoid connecting to the server on every call.
*   The implementation is focused solely on the `sse` transport for the MVP.

## Future Considerations (Not for MVP)

*   Support for `stdio` and `http` transports.
*   Handling `list_resources` and `read_resource`.
*   Interactive mode for complex conversations with an MCP server.
