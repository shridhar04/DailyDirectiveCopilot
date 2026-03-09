from __future__ import annotations

from pydantic import BaseModel, Field


class MCPToolRequest(BaseModel):
    tool_name: str
    payload: dict = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    tool_name: str
    ok: bool
    payload: dict = Field(default_factory=dict)
    error: str | None = None