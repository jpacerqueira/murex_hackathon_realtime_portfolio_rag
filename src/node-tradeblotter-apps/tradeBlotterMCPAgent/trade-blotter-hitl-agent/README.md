# Trade Blotter HITL Agent

A runnable [Google ADK](https://google.github.io/adk-docs/) agent package that
talks to a Trade Blotter [MCP](https://modelcontextprotocol.io/) server through
the FastAPI HTTP bridge defined in `mcp_http_server.py`. Read-only MCP tools
execute directly; mutating tools (place / cancel / amend / etc.) are gated by
a Human-in-the-Loop approval step using ADK's `LongRunningFunctionTool`.

The package is also a self-contained **Agent Skill** following the
[agentskills.io specification](https://agentskills.io/specification): the root
contains a `SKILL.md`, plus `scripts/`, `references/`, and `assets/`
directories.

## Why this exists

The reference Trade Blotter MCP server runs over stdio and is wrapped by
`mcp_http_server.py`, a tiny FastAPI bridge that exposes the MCP surface as
plain REST. That makes it trivial for *any* HTTP-capable agent runtime to use
the blotter, but it also strips away the usual MCP transport-level safety
features. This package gives you back a strong, opinionated default:

* Tool discovery happens at startup against `/tools`.
* Each tool is classified as `read_only` or `mutating` (see
  `assets/tool_classification.yaml`).
* A single `request_trade_action` `LongRunningFunctionTool` is the only path
  to a mutating call. The runner pauses; a human approves or rejects; the
  agent then calls the corresponding `execute_<name>` tool, which is
  defended by a `before_tool_callback` checking the approval ticket.

## Run with Docker Compose (recommended)

This repo already has a `docker-compose.yml` at the project root with
`trade-api`, `mcp-server`, and `desktop-app`. The agent is wired in as a
fourth service called `trade-blotter-hitl-agent` on the same `mcp-hackathon`
network.

```bash
# from the project root (where docker-compose.yml lives)
export GOOGLE_API_KEY=...                    # or GEMINI_API_KEY
docker compose up --build trade-blotter-hitl-agent
```

The agent's web UI is published at **http://localhost:8200** (host port
8200 → container 8000, since `trade-api` already owns 8000 on the host).
Inside the network it talks to `http://mcp-server:7001`.

What happens at boot:

1. The container's entrypoint waits up to 120 seconds for
   `http://mcp-server:7001/health` to respond. (The compose file also gates
   the agent on `mcp-server`'s healthcheck via
   `depends_on: condition: service_healthy`.)
2. The startup log dumps every MCP tool / resource / prompt the bridge
   exposes — handy for sanity-checking classification rules.
3. `adk web` starts on `0.0.0.0:8000`. Open the browser at port 8200, pick
   the `trade_blotter_hitl_agent` app, and chat. When the model calls
   `request_trade_action`, the web UI surfaces a pending FunctionCall and
   lets you respond with an approval `FunctionResponse` — that's the HITL
   loop.

Stop the agent without touching the rest of the stack:

```bash
docker compose stop trade-blotter-hitl-agent
docker compose rm -f trade-blotter-hitl-agent
```

Bring everything up:

```bash
docker compose up --build
```

### Container-only environment variables

| Variable                    | Default                       | Meaning                                                          |
| --------------------------- | ----------------------------- | ---------------------------------------------------------------- |
| `MCP_BRIDGE_URL`            | `http://mcp-server:7001`      | Where the agent finds the bridge inside the compose network.     |
| `MCP_BRIDGE_TIMEOUT`        | `30`                          | HTTP timeout per bridge call.                                    |
| `MCP_BRIDGE_WAIT_SECONDS`   | `120`                         | How long the entrypoint polls `/health` before giving up.        |
| `MCP_LIST_TOOLS_ON_STARTUP` | `true`                        | Dump the discovered tool surface to container logs at boot.      |
| `GOOGLE_API_KEY`            | (forwarded from host)         | Required by ADK's Gemini client.                                 |
| `ADK_MODEL`                 | `gemini-3.1-pro-preview`      | Override to use a different Gemini model.                        |
| `HITL_FAIL_CLOSED`          | `true`                        | Treat unknown MCP tools as mutating (require approval).          |
| `TOOL_CLASSIFICATION_PATH`  | `/app/assets/tool_classification.yaml` | Override the classification YAML inside the image.        |

## Install (local dev, without Docker)

Requires Python 3.10+.

```bash
cd trade-blotter-hitl-agent
uv venv && source .venv/bin/activate
uv pip install -e .[dev]
```

(or `python -m venv .venv && pip install -e .[dev]`)

## Configure

```bash
cp .env.example .env
$EDITOR .env
```

Minimum settings:

| Variable          | Purpose                                                  |
| ----------------- | -------------------------------------------------------- |
| `MCP_BRIDGE_URL`  | Where `mcp_http_server.py` is listening.                 |
| `GOOGLE_API_KEY`  | Gemini API key (or use Vertex AI env vars instead).      |
| `ADK_MODEL`       | Defaults to `gemini-3.1-pro-preview`.                    |

## Run

Start the MCP HTTP bridge in one terminal:

```bash
uvicorn mcp_http_server:app --host 0.0.0.0 --port 8080
```

Smoke-test that the agent can see it:

```bash
python scripts/list_mcp_tools.py
# or, after install:
trade-blotter-list-tools
```

Then run the agent:

```bash
adk run trade_blotter_hitl_agent      # terminal chat
# or
adk web                               # browser dev UI
```

## How a mutating call flows

```
user: "cancel trade T-123 on AAPL"
agent: list_open_trades()                              # read-only, runs immediately
agent: request_trade_action(
            tool="cancel_trade",
            arguments={"trade_id": "T-123"},
            rationale="user asked to cancel T-123")
runner: pauses with FunctionCall {request_trade_action ...}
host:   surfaces ticket "tb-1a2b3c4d" to a human
human:  approves
host:   sends FunctionResponse {status:"approved", ticketId:"tb-1a2b3c4d", ...}
agent: execute_cancel_trade(ticket_id="tb-1a2b3c4d", trade_id="T-123")
                # before_tool_callback verifies the ticket
                # then the bridge POST /tool/cancel_trade is hit
agent: "T-123 cancelled at 14:02:11."
```

See `references/ADK_HITL.md` for the annotated FunctionResponse shape.

## Tests

```bash
pytest -q
```

The test suite uses `respx` to mock the MCP HTTP bridge — no real network is
needed.

## Validating the skill

```bash
pipx run skills-ref validate ./
```

## Layout

```
trade-blotter-hitl-agent/
├── SKILL.md
├── README.md
├── pyproject.toml
├── .env.example
├── Dockerfile                    # multi-stage agent image
├── .dockerignore
├── docker/
│   └── entrypoint.sh             # wait-for-bridge + adk web launcher
├── trade_blotter_hitl_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── mcp_client.py
│   ├── tool_factory.py
│   ├── hitl.py
│   ├── prompts.py
│   ├── config.py
│   └── scripts_entry.py
├── scripts/
│   ├── list_mcp_tools.py
│   └── run_dev.sh
├── references/
│   ├── ADK_HITL.md
│   ├── MCP_BRIDGE.md
│   └── SECURITY.md
├── assets/
│   └── tool_classification.yaml
└── tests/
    ├── test_mcp_client.py
    └── test_tool_factory.py
```

The merged `docker-compose.yml` lives one level up, alongside `tradeQueryApi/`,
`mcp/`, and `desktopApp/`.
