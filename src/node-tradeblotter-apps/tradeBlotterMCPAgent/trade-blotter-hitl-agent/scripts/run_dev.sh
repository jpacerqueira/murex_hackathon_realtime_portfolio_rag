#!/usr/bin/env bash
# Launch the agent in ADK's developer web UI. Useful for testing the HITL flow:
# the web UI shows pending FunctionCalls and lets you respond with a
# FunctionResponse.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

if [[ ! -f .env ]]; then
  echo "warning: no .env file; copy .env.example and fill it in" >&2
fi

# Quick reachability probe.
python scripts/list_mcp_tools.py >/dev/null || {
  echo "MCP HTTP bridge unreachable. Start mcp_http_server.py first." >&2
  exit 1
}

exec adk web
