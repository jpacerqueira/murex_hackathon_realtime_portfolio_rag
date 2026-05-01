---
name: trade-blotter-hitl-agent
description: Builds and runs a Google ADK (Agent Development Kit) agent that talks to a Trade Blotter MCP server through its HTTP bridge (mcp_http_server.py). Tools exposed by the MCP server are auto-discovered, read-only tools execute directly, and mutating/sensitive tools are gated by a Human-in-the-Loop approval step using ADK's LongRunningFunctionTool. Use when you need an ADK agent that lists, queries, places, cancels, or modifies trades against an MCP-backed blotter and want every state-changing call confirmed by a human before it runs.
license: Apache-2.0
compatibility: Runs locally on Python 3.10+ (google-adk>=0.6, httpx, pydantic), or as a Docker container alongside the existing Murex hackathon stack via the supplied Dockerfile and docker-compose.yml (services trade-api, mcp-server, desktop-app, trade-blotter-hitl-agent on the mcp-hackathon network). Requires a Google AI Studio API key (or Vertex AI credentials) and a reachable Trade Blotter MCP HTTP bridge (mcp_http_server.py).
metadata:
  author: qodea
  version: "1.0.0"
  agent-framework: google-adk
  mcp-transport: http-bridge
  hitl-pattern: long-running-function-tool
allowed-tools: Read Edit Write Bash(uv:*) Bash(python:*) Bash(adk:*)
---

# Trade Blotter HITL Agent skill

## What this skill does

This skill installs and configures a runnable Google **Agent Development Kit (ADK)**
agent package that connects to a Trade Blotter **Model Context Protocol (MCP)**
server through the HTTP bridge defined in `mcp_http_server.py`. The bridge
exposes the underlying MCP server's `list_tools`, `list_resources`, `list_prompts`,
`call_tool`, `read_resource`, and `get_prompt` over plain REST so an ADK agent can
consume them without an MCP stdio client.

The agent applies the **Human-in-the-Loop (HITL)** pattern from the ADK
`human_in_loop` sample: tools that *change state* (place trade, cancel trade,
amend, etc.) are wrapped as `LongRunningFunctionTool` and return a `pending`
status. The runner pauses, the human approves or rejects, the agent then either
calls the real execution tool or reports the rejection. Read-only tools (list,
get, search) are exposed as plain `FunctionTool` and execute immediately.

## When to use this skill

- You have an MCP server (with the `mcp_http_server.py` FastAPI bridge from this
  pattern) and want a chat-style agent on top of it.
- You need an audit-friendly trading or operations agent: every write must be
  approved by a human before it hits the MCP server.
- You want the ADK `adk run` / `adk web` developer loop to drive the agent.

Do **not** use this skill for: agents that should execute trades autonomously,
non-MCP back-ends, or front-ends that need streaming voice/video.

## Quick start

### Docker Compose (recommended for the hackathon stack)

```bash
# from the project root, alongside the existing docker-compose.yml
export GOOGLE_API_KEY=...        # or GEMINI_API_KEY
docker compose up --build trade-blotter-hitl-agent
# Web UI: http://localhost:8200  (host 8200 -> container 8000)
```

The agent reaches the bridge at `http://mcp-server:7001` on the
`mcp-hackathon` network, waits for the bridge's `/health` to respond, then
launches `adk web` on container port 8000 (published to host port 8200).

### Local Python

```bash
# 1. Install
cd trade-blotter-hitl-agent
uv venv && source .venv/bin/activate
uv pip install -e .

# 2. Configure
cp .env.example .env
# edit .env to set MCP_BRIDGE_URL and GOOGLE_API_KEY

# 3. Smoke test the bridge
python scripts/list_mcp_tools.py

# 4. Run the agent (terminal UI)
adk run trade_blotter_hitl_agent

# Or open the dev web UI
adk web
```

When you ask the agent to do something mutating (e.g. "place a buy of 100 AAPL
at limit 200"), the agent will invoke `request_trade_action`, which is a
`LongRunningFunctionTool` that returns `{"status": "pending", ...}`. The
runner pauses; you respond with an approval `FunctionResponse`; the agent then
calls the matching `execute_*` tool against the MCP bridge.

## Package layout

```
trade-blotter-hitl-agent/
├── SKILL.md                        # this file (agentskills.io spec)
├── README.md                       # human-facing docs
├── pyproject.toml                  # package + entry points
├── .env.example                    # MCP_BRIDGE_URL, GOOGLE_API_KEY, etc.
├── trade_blotter_hitl_agent/
│   ├── __init__.py                 # exports root_agent for `adk run`
│   ├── agent.py                    # ADK LlmAgent definition
│   ├── mcp_client.py               # httpx client over the HTTP bridge
│   ├── tool_factory.py             # turns MCP tools into ADK FunctionTools
│   ├── hitl.py                     # approval helpers + LongRunningFunctionTool
│   ├── prompts.py                  # agent instruction
│   └── config.py                   # env-driven settings
├── scripts/
│   ├── list_mcp_tools.py           # smoke test
│   └── run_dev.sh                  # convenience launcher
├── references/
│   ├── ADK_HITL.md                 # how the LongRunningFunctionTool flow works
│   ├── MCP_BRIDGE.md               # the bridge's REST surface
│   └── SECURITY.md                 # what HITL does and does not protect
├── assets/
│   └── tool_classification.yaml    # which MCP tools require approval
└── tests/
    ├── test_mcp_client.py          # mocked-bridge tests
    └── test_tool_factory.py        # classification + wrapping tests
```

## How the HITL gate works (one-paragraph version)

For every MCP tool listed by the bridge, the factory looks it up in
`assets/tool_classification.yaml`. Tools tagged `read_only` become a normal
ADK `FunctionTool`. Tools tagged `mutating` are exposed as a *pair*:

1. `request_<tool>(args)` — a `LongRunningFunctionTool` that returns
   `{"status": "pending", "ticketId": "...", "tool": "<tool>", "args": args}`.
2. `execute_<tool>(args)` — a regular `FunctionTool` that calls the MCP bridge.

The agent's instruction (see `prompts.py`) tells the model to **always** call
`request_<tool>` first for mutating actions and only call `execute_<tool>` once
the runner has surfaced an approved `FunctionResponse`. A second-line
defence — a `before_tool_callback` on the agent — refuses any direct
`execute_<tool>` call that doesn't have a matching approval ticket in
`tool_context.state`.

## Editing the classification

Add/remove tool patterns in `assets/tool_classification.yaml`. Patterns are
matched against the MCP tool name in order; the first match wins. Default rules
classify common verbs: `list_*`, `get_*`, `search_*`, `read_*` are read-only;
`place_*`, `cancel_*`, `amend_*`, `modify_*`, `submit_*`, `delete_*`, `create_*`
are mutating; everything else falls back to `mutating` (fail closed).

## References

- `references/ADK_HITL.md` — annotated flow with code snippets.
- `references/MCP_BRIDGE.md` — REST surface of `mcp_http_server.py`.
- `references/SECURITY.md` — threat model and limits of HITL.

## Validation

```bash
# Validate this skill against the agentskills.io spec
pipx run skills-ref validate ./

# Smoke-test the package
python scripts/list_mcp_tools.py
pytest -q
```
