# agent-orchestration-mcp

A learning project that **builds and orchestrates a team of LLM agents** which collaborate
to research a question and produce a cited report. It uses:

- **Multiple agents** (Planner → Researcher → Analyst/Synthesizer → Editor) coordinated by an orchestrator.
- The **Model Context Protocol (MCP)**: a standalone tool *server* (web search + page fetch) that the app connects to as an MCP *client*.
- An **LLM SDK** (Anthropic / Claude) with a hand-rolled tool-use loop.
- **Live web retrieval** (RAG-adjacent grounding) so answers are backed by real sources.

> This repo is a personal learning project. The code is intentionally **stubbed and
> heavily commented** to teach the concepts. See [`DESIGN.md`](./DESIGN.md) for the full
> architecture, the process model, and the rationale behind every decision.

## Status

🚧 **Skeleton / scaffolding.** Functions are stubbed with docstrings, TODOs, and concept
notes. v1 logic is not implemented yet.

## At a glance

- **Runtime processes (v1):** 2 local processes — the app (MCP *client*) and the stdio MCP
  *server* — plus the remote Anthropic API. (Agents are *roles within one process*, not
  separate processes. See DESIGN.md.)
- **Transport:** stdio for v1, with a wrapper that lets us migrate to Streamable HTTP later.
- **Search:** Tavily (free tier) by default, with DuckDuckGo as a no-key fallback.

## Quickstart (placeholder — not runnable yet)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env   # then edit .env and add your keys

# 4. (Once implemented) run a research task
python main.py "What are the trade-offs of MCP vs. plain function calling?"
```

## Project layout

```
agent-orchestration-mcp/
├── README.md
├── DESIGN.md                 # full design doc — start here
├── requirements.txt
├── .env.example
├── .gitignore
├── mcp_server/               # the MCP TOOL SERVER (decoupled from agents)
│   └── research_tools.py     # web_search + fetch_url tools (FastMCP, stdio)
├── orchestration/            # the APP: agents + orchestrator + MCP client
│   ├── config.py
│   ├── llm.py                # Anthropic wrapper + hand-rolled agent loop
│   ├── mcp_client.py         # MCP client session factory (parallel-ready)
│   ├── state.py              # ResearchState shared between agents
│   ├── orchestrator.py       # wires planner -> researcher(s) -> analyst -> editor
│   └── agents/
│       ├── planner.py
│       ├── researcher.py
│       ├── analyst.py
│       └── editor.py
└── main.py                   # CLI entrypoint
```

## Git & PR workflow

`main` is the default branch. All file changes land via **feature branches and pull
requests** — see the "Git & PR workflow" section in [`DESIGN.md`](./DESIGN.md).
