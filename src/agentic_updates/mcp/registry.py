from __future__ import annotations

from collections.abc import Callable

from agentic_updates.mcp.protocol import MCPToolRequest, MCPToolResponse


ToolHandler = Callable[[dict], dict]


class MCPToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, tool_name: str, handler: ToolHandler) -> None:
        self._handlers[tool_name] = handler

    def invoke(self, request: MCPToolRequest) -> MCPToolResponse:
        handler = self._handlers.get(request.tool_name)
        if handler is None:
            return MCPToolResponse(
                tool_name=request.tool_name,
                ok=False,
                error=f"Unknown tool: {request.tool_name}",
            )

        try:
            payload = handler(request.payload)
            return MCPToolResponse(tool_name=request.tool_name, ok=True, payload=payload)
        except Exception as exc:  # pragma: no cover
            return MCPToolResponse(
                tool_name=request.tool_name,
                ok=False,
                error=str(exc),
            )
