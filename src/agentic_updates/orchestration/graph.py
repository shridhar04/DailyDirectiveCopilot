from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agentic_updates.agents import EmailAgent, JiraAgent, MeetingNotesAgent, SlackAgent
from agentic_updates.connectors import (
    EmailConnector,
    JiraConnector,
    MeetingNotesConnector,
    SlackConnector,
)
from agentic_updates.llm import LLMSummaryService
from agentic_updates.mcp.protocol import MCPToolRequest
from agentic_updates.mcp.registry import MCPToolRegistry
from agentic_updates.models import Signal, SummaryOutput
from agentic_updates.orchestration.state import WorkflowState
from agentic_updates.summary import (
    deduplicate_tasks,
    generate_summary_bullets,
    merge_signals,
    rank_tasks,
)


@dataclass
class WorkflowRuntime:
    jira_agent: JiraAgent
    slack_agent: SlackAgent
    email_agent: EmailAgent
    meeting_notes_agent: MeetingNotesAgent


def build_workflow_runtime(data_dir: str = "data") -> WorkflowRuntime:
    base = Path(data_dir)
    return WorkflowRuntime(
        jira_agent=JiraAgent(JiraConnector(base)),
        slack_agent=SlackAgent(SlackConnector(base)),
        email_agent=EmailAgent(EmailConnector(base)),
        meeting_notes_agent=MeetingNotesAgent(MeetingNotesConnector(base)),
    )


class UpdatesWorkflow:
    def __init__(self, data_dir: str = "data") -> None:
        self.runtime = build_workflow_runtime(data_dir=data_dir)
        self.registry = MCPToolRegistry()
        self.llm_summary = LLMSummaryService()
        self._register_tools()
        self.graph = self._build_graph().compile()

    def _register_tools(self) -> None:
        self.registry.register(
            "jira_connector",
            lambda _: {"signals": [s.model_dump(mode="json") for s in self.runtime.jira_agent.run()]},
        )
        self.registry.register(
            "slack_connector",
            lambda _: {
                "signals": [s.model_dump(mode="json") for s in self.runtime.slack_agent.run()]
            },
        )
        self.registry.register(
            "email_connector",
            lambda _: {
                "signals": [s.model_dump(mode="json") for s in self.runtime.email_agent.run()]
            },
        )
        self.registry.register(
            "meeting_notes_connector",
            lambda _: {
                "signals": [
                    s.model_dump(mode="json") for s in self.runtime.meeting_notes_agent.run()
                ]
            },
        )

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(WorkflowState)
        graph.add_node("collect_signals", self.collect_signals)
        graph.add_node("merge_context", self.merge_context)
        graph.add_node("deduplicate_tasks", self.deduplicate_tasks)
        graph.add_node("rank_urgency", self.rank_urgency)
        graph.add_node("generate_summary", self.generate_summary)

        graph.add_edge(START, "collect_signals")
        graph.add_edge("collect_signals", "merge_context")
        graph.add_edge("merge_context", "deduplicate_tasks")
        graph.add_edge("deduplicate_tasks", "rank_urgency")
        graph.add_edge("rank_urgency", "generate_summary")
        graph.add_edge("generate_summary", END)
        return graph

    def collect_signals(self, state: WorkflowState) -> WorkflowState:
        tool_names = [
            "jira_connector",
            "slack_connector",
            "email_connector",
            "meeting_notes_connector",
        ]
        all_signals: list[Signal] = []

        for name in tool_names:
            response = self.registry.invoke(MCPToolRequest(tool_name=name))
            if not response.ok:
                continue
            for row in response.payload.get("signals", []):
                all_signals.append(Signal.model_validate(row))

        return {
            "signals": all_signals,
            "tasks": state.get("tasks", []),
            "summary": state.get("summary", SummaryOutput()),
        }

    def merge_context(self, state: WorkflowState) -> WorkflowState:
        merged = merge_signals(state.get("signals", []))
        return {"signals": merged, "tasks": state.get("tasks", []), "summary": state.get("summary", SummaryOutput())}

    def deduplicate_tasks(self, state: WorkflowState) -> WorkflowState:
        tasks = deduplicate_tasks(state.get("signals", []))
        return {"signals": state.get("signals", []), "tasks": tasks, "summary": state.get("summary", SummaryOutput())}

    def rank_urgency(self, state: WorkflowState) -> WorkflowState:
        ranked = rank_tasks(state.get("tasks", []))
        return {"signals": state.get("signals", []), "tasks": ranked, "summary": state.get("summary", SummaryOutput())}

    def generate_summary(self, state: WorkflowState) -> WorkflowState:
        tasks = state.get("tasks", [])
        bullets = self.llm_summary.generate_bullets(tasks) or generate_summary_bullets(tasks)
        output = SummaryOutput(bullets=bullets, tasks=tasks)
        return {"signals": state.get("signals", []), "tasks": tasks, "summary": output}

    def run(self) -> SummaryOutput:
        initial: WorkflowState = {"signals": [], "tasks": [], "summary": SummaryOutput()}
        result = self.graph.invoke(initial)
        return result["summary"]
