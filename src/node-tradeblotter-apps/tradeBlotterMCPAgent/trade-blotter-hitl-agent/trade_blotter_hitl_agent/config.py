"""Environment-driven configuration for the Trade Blotter HITL agent."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from `.env` / process environment.

    Attributes are documented inline; see `.env.example` for the canonical list.
    """

    # --- MCP HTTP bridge ---
    mcp_bridge_url: str = Field(
        default="http://localhost:8080",
        validation_alias="MCP_BRIDGE_URL",
        description="Base URL of mcp_http_server.py.",
    )
    mcp_bridge_timeout: float = Field(
        default=30.0,
        validation_alias="MCP_BRIDGE_TIMEOUT",
        description="HTTP timeout for bridge calls, in seconds.",
    )
    mcp_bridge_token: Optional[str] = Field(
        default=None,
        validation_alias="MCP_BRIDGE_TOKEN",
        description="Optional bearer token if the bridge is auth-protected.",
    )

    # --- Model ---
    adk_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="ADK_MODEL",
        description="Gemini model name used by the agent.",
    )

    # --- HITL ---
    tool_classification_path: str = Field(
        default="assets/tool_classification.yaml",
        validation_alias="TOOL_CLASSIFICATION_PATH",
        description="Path (relative to the package root or absolute) to the YAML "
        "that classifies MCP tools as read_only / mutating.",
    )
    hitl_fail_closed: bool = Field(
        default=True,
        validation_alias="HITL_FAIL_CLOSED",
        description="If True, MCP tools that don't match any classification rule "
        "are treated as mutating (require approval).",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolve_classification_path(self, package_root: Path) -> Path:
        """Resolve the classification YAML path against the package root."""
        candidate = Path(self.tool_classification_path)
        if candidate.is_absolute():
            return candidate
        return (package_root / candidate).resolve()


settings = Settings()
