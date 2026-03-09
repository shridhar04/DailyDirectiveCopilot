from __future__ import annotations

from agentic_updates.mcp.protocol import MCPToolRequest
from agentic_updates.mcp.registry import MCPToolRegistry
from agentic_updates.orchestration.graph import build_workflow_runtime


def create_registry_with_agents(data_dir: str = "data") -> MCPToolRegistry:
    runtime = build_workflow_runtime(data_dir=data_dir)
    registry = MCPToolRegistry()

    registry.register(
        "jira_connector",
        lambda _: {"signals": [s.model_dump(mode="json") for s in runtime.jira_agent.run()]},
    )
    registry.register(
        "slack_connector",
        lambda _: {"signals": [s.model_dump(mode="json") for s in runtime.slack_agent.run()]},
    )
    registry.register(
        "email_connector",
        lambda _: {"signals": [s.model_dump(mode="json") for s in runtime.email_agent.run()]},
    )
    registry.register(
        "meeting_notes_connector",
        lambda _: {
            "signals": [s.model_dump(mode="json") for s in runtime.meeting_notes_agent.run()]
        },
    )
    return registry


def serve_stdio(data_dir: str = "data") -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "MCP package missing or incompatible. Install requirements first."
        ) from exc

    registry = create_registry_with_agents(data_dir=data_dir)
    server = FastMCP("agentic-updates-hub")

    @server.tool()
    def jira_connector() -> dict:
        return registry.invoke(MCPToolRequest(tool_name="jira_connector")).payload

    @server.tool()
    def slack_connector() -> dict:
        return registry.invoke(MCPToolRequest(tool_name="slack_connector")).payload

    @server.tool()
    def email_connector() -> dict:
        return registry.invoke(MCPToolRequest(tool_name="email_connector")).payload

    @server.tool()
    def meeting_notes_connector() -> dict:
        return registry.invoke(MCPToolRequest(tool_name="meeting_notes_connector")).payload

    server.run(transport="stdio")


if __name__ == "__main__":
    serve_stdio()
