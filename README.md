# Agentic Updates Hub

Agentic AI project that collects updates from Jira, Slack, Email, and Meeting Notes, then produces a single urgency-ranked summary for employees.

## What it does

- Uses dedicated agents:
  - Jira Agent
  - Slack Agent
  - Email Agent
  - Meeting Notes Agent
  - Summary Agent
- Uses LangGraph for orchestration:
  1. Collect signals
  2. Merge context
  3. Deduplicate tasks
  4. Rank by urgency
  5. Generate summary
- Uses an MCP-style tool contract (request/response schema + registry) for standardized connector communication.
- Includes an optional MCP server (`mcp.server.fastmcp`) to expose connectors as tools.

## Live connectors

- Jira connector: Atlassian REST API via `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`
- Slack connector: Slack Web API (`conversations.history`) via `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_IDS`
- Email connector: IMAP via `EMAIL_IMAP_HOST`, `EMAIL_IMAP_USERNAME`, `EMAIL_IMAP_PASSWORD`
- Meeting notes connector: local JSON file (`data/meeting_notes.json`)

If any live connector credentials are missing or API calls fail, that connector automatically falls back to local sample JSON.

## Project structure

`src/agentic_updates/`
- `connectors/` Source connectors for Jira/Slack/Email/Meeting notes
- `agents/` Agent wrappers around connectors
- `mcp/` Standardized tool protocol, registry, optional server
- `orchestration/` LangGraph state and workflow
- `summary.py` Dedup/ranking/summary logic
- `main.py` CLI entrypoint

`data/`
- Example datasets for local run

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Create env file:

```bash
copy .env.example .env
```

Fill `.env` values for Jira/Slack/Email credentials.

## Run

```bash
python run.py
```

Optional arguments:

```bash
python run.py --data-dir data --output summary.md
```

## Optional: run MCP tool server

```bash
$env:PYTHONPATH='src'; python -m agentic_updates.mcp.server
```

This starts a local MCP stdio server exposing connector tools.
