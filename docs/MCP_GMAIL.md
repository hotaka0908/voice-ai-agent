MCP Gmail Integration (Draft)
=============================

Purpose
- Use MCP (Model Context Protocol) to let the Voice Agent access Gmail via a dedicated MCP server, so the AI can read/search emails or draft/send messages with consistent tool semantics.

Server Assumptions
- Transport: HTTP JSON-RPC (single POST endpoint)
- Auth: Bearer token
- Methods (typical MCP shape; adapt to your server):
  - `tools/call` with params `{ "name": string, "arguments": object }`
  - `resources/read` with params `{ "uri": string, "options": object }`

Examples (tool names)
- `gmail.list_messages` arguments: `{ "query": "is:unread newer_than:7d", "max": 10 }`
- `gmail.get_message` arguments: `{ "id": "<messageId>" }`
- `gmail.create_draft` arguments: `{ "to": "user@example.com", "subject": "Hi", "body": "Hello" }`
- `gmail.send_message` arguments: `{ "to": "user@example.com", "subject": "Hi", "body": "Hello" }`

Client Configuration
- Set `MCP_SERVERS` in `.env` with a JSON map. Example:

```
MCP_SERVERS={
  "gmail": {
    "endpoint": "http://localhost:9101/rpc",
    "token": "your_bearer_token",
    "transport": "http_jsonrpc"
  }
}
```

How the Agent Calls It
- The `mcp` tool accepts:
  - `server`: e.g. `gmail`
  - `action`: `tool` (call a tool) or `resource` (read a resource)
  - `name`: tool name (e.g. `gmail.list_messages`) or resource uri for `resource`
  - `arguments`: tool arguments (object)

Examples via LLM tool-calling (pseudocode)

1) List unread messages
```
TOOL_CALL: {"name": "mcp", "parameters": {
  "server": "gmail",
  "action": "tool",
  "name": "gmail.list_messages",
  "arguments": {"query": "is:unread newer_than:7d", "max": 10}
}}
```

2) Read one message
```
TOOL_CALL: {"name": "mcp", "parameters": {
  "server": "gmail",
  "action": "tool",
  "name": "gmail.get_message",
  "arguments": {"id": "<messageId>"}
}}
```

3) Draft or send an email (confirm via voice before sending)
```
TOOL_CALL: {"name": "mcp", "parameters": {
  "server": "gmail",
  "action": "tool",
  "name": "gmail.send_message",
  "arguments": {
    "to": "friend@example.com",
    "subject": "出発しました",
    "body": "今から向かいます。15分ほどで着きます。"
  }
}}
```

Security Notes
- Keep the MCP server isolated; store OAuth tokens on that server only.
- Enforce scope per tool; dangerous operations (send/delete) should require an explicit confirmation channel (voice prompt or second factor).
- Rate-limit and log minimal PII (mask content in logs).

Next Steps
- Implement your Gmail MCP server (Node/Python) to expose the above JSON-RPC surface.
- Move the Agent’s LLM to native tool/function-calling with the `mcp` schema for robust calls.
