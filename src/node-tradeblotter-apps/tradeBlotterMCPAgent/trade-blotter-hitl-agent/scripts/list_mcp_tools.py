#!/usr/bin/env python3
"""Print every tool / resource / prompt the MCP HTTP bridge exposes.

Run this first to confirm the bridge is reachable before launching `adk run`.

Usage:
    python scripts/list_mcp_tools.py
    # or, after `pip install -e .`:
    trade-blotter-list-tools

Reads MCP_BRIDGE_URL from `.env` (or process env). Defaults to
http://localhost:8080.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from a checkout without installing the package.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trade_blotter_hitl_agent.scripts_entry import list_tools_main


if __name__ == "__main__":
    list_tools_main()
