# MCP HTTP bridge — reference

The bridge (`mcp_http_server.py`) is a thin FastAPI shim over the underlying
MCP server's stdio surface. It exposes:

| Method | Path                  | Body                                  | Returns                                  |
| ------ | --------------------- | ------------------------------------- | ---------------------------------------- |
| GET    | `/health`             | —                                     | `{"status": "healthy"}`                  |
| GET    | `/tools`              | —                                     | `[ToolSpec, ...]`                        |
| GET    | `/resources`          | —                                     | `[ResourceSpec, ...]`                    |
| GET    | `/prompts`            | —                                     | `[PromptSpec, ...]`                      |
| GET    | `/resource?uri=<uri>` | —                                     | `{"uri": "...", "content": ...}`         |
| POST   | `/tool/{name}`        | `{"arguments": { ... }}`              | `{"name": "...", "content": [item, ...]}`|
| POST   | `/prompt/{name}`      | `{"arguments": { ... }}`              | `{"messages": [...]}` (with API docs prepended) |

`ToolSpec` is whatever the underlying MCP server's `list_tools()` produces,
serialised through `model_dump()`. The bridge does not stabilise the field
names; `mcp_client.ToolSpec.from_dict` accepts both `inputSchema` and
`input_schema`.

## `content` shape

`POST /tool/{name}` returns `content` as a list of MCP content items. Common
shapes:

```jsonc
// Plain text result
{"name": "list_open_trades",
 "content": [{"type": "text", "text": "[{\"id\":\"T-123\",...}]"}]}

// Structured result
{"name": "get_trade",
 "content": [{"type": "text", "text": "{\"id\":\"T-123\",\"qty\":100}"}]}
```

`mcp_client._content_to_python` flattens these to a single Python value
(decoding the `text` payload as JSON when possible) so tool callables in
`tool_factory.py` see a clean dict / list / string instead of the raw
protocol envelope.

## Errors

The bridge returns `400` with `{"detail": "..."}` for any exception in the
underlying MCP server. `MCPHTTPClient` raises `MCPBridgeError` carrying the
status and body; the tool factory catches it and surfaces it to the LLM as
`{"status": "error", "tool": "...", "error": "..."}`.

## Auth

The bridge ships without authentication. If you front it with an auth proxy
(e.g. an OAuth2 sidecar or an API gateway), set `MCP_BRIDGE_TOKEN` in `.env`
and the client will send `Authorization: Bearer <token>`.

## Running locally

```bash
uvicorn mcp_http_server:app --host 0.0.0.0 --port 8080
```

The bridge imports `mcp_server` (a sibling module) at startup and re-exports
its async functions; that module needs to be on `PYTHONPATH`.
