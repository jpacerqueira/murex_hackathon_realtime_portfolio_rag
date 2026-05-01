#!/usr/bin/env bash
# Wait for the MCP HTTP bridge before launching ADK.
#
# Reads MCP_BRIDGE_URL from the environment (defaults to http://mcp-server:7001
# to match the docker-compose layout). Polls /health until it responds or
# until MCP_BRIDGE_WAIT_SECONDS elapses (default 60). If the bridge never
# comes up, the agent still starts in the degraded mode coded into agent.py —
# but we'd rather wait so the LLM sees the real tool surface on first token.

set -euo pipefail

BRIDGE_URL="${MCP_BRIDGE_URL:-http://mcp-server:7001}"
WAIT="${MCP_BRIDGE_WAIT_SECONDS:-60}"
INTERVAL=2
ELAPSED=0

echo "[entrypoint] waiting up to ${WAIT}s for MCP bridge at ${BRIDGE_URL}/health"
while (( ELAPSED < WAIT )); do
  if curl -fsS --max-time 2 "${BRIDGE_URL%/}/health" >/dev/null 2>&1; then
    echo "[entrypoint] bridge healthy after ${ELAPSED}s"
    break
  fi
  sleep "${INTERVAL}"
  ELAPSED=$(( ELAPSED + INTERVAL ))
done

if (( ELAPSED >= WAIT )); then
  echo "[entrypoint] WARNING: MCP bridge never became healthy; agent will start in degraded mode" >&2
fi

# `adk web` needs to know where the agent package lives. We `cd /app` so it
# discovers `trade_blotter_hitl_agent/` as a sibling directory.
cd /app

echo "[entrypoint] launching: $*"
exec "$@"
