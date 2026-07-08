# agent-orchestration-mcp

`maestro` is a multi-agent system that researches a prompt and writes a cited report, using
LLMs, agents, and the Model Context Protocol (MCP).

> **Status:** Researcher agent with live Anthropic tool-use loop. Copy `.env.example` to
> `.env` for local secrets; the orchestrator loads `.env` automatically on startup.

## Architecture

Maestro coordinates four agent roles (planner → researcher → analyst → editor) in one
application process, talks to a standalone MCP tool server over stdio, and calls the
Anthropic API for LLM steps. For process model, agent roles, architecture tradeoffs,
and v1 scope, see **[DESIGN.md](DESIGN.md)**.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency and environment management

## Installation

```bash
uv sync
cp .env.example .env
```

Edit `.env` and set your real `ANTHROPIC_API_KEY`. This creates a project-local virtual
environment in `.venv/` and installs dependencies.

`src/maestro/settings.py` defines settings via a `Settings` dataclass and exports a
module-level `settings` object.
On startup, `load_settings()` applies `.env` values over dataclass defaults. LLM and MCP
tuning defaults live in the `Settings` dataclass; `.env` is mainly for secrets like the
API key. Tests set `dummy-anthropic-api-key` via pytest fixtures so they never skip for
a missing key.

## Usage

Activate the environment, then run the CLI:

```bash
source .venv/bin/activate

maestro "What are the trade-offs of MCP versus plain function calling?"
# equivalently:
python -m maestro "What are the trade-offs of MCP versus plain function calling?"
```

Or run without activating: `uv run maestro "..."`.

The application imports the module-level `settings` object from `src/maestro/settings.py`,
which is built by `load_settings()` using `.env` at process startup.
You do not need to `export` variables manually for local development.

### MCP tool server

Start the fetch-url MCP server (stdio transport) in a separate process:

```bash
uv run maestro-mcp
# equivalently:
uv run python -m maestro.mcp_server
```

## Development

With the environment activated (no prefix needed):

```bash
pytest                 # run the test suite
ruff check .           # lint
ruff format .          # format
pre-commit install     # optional: run ruff automatically on each commit
```

Any command also works prefixed with `uv run`. Continuous integration runs lint, format
check, and tests on every pull request to `main`.

## Project structure

`DESIGN.md` describes the target layout. This tree reflects what exists today:

```
agent-orchestration-mcp/
├── pyproject.toml                # project metadata, dependencies, tooling config
├── DESIGN.md                     # architecture and design decisions
├── .env.example                  # env template (copy to .env)
├── .pre-commit-config.yaml       # ruff lint/format on commit
├── .github/workflows/ci.yml      # lint + test on each PR
├── src/maestro/
│   ├── __main__.py               # enables `python -m maestro`
│   ├── cli.py                    # command-line entry point
│   ├── settings.py              # defaults + env overrides
│   ├── orchestrator.py           # coordinates the agent pipeline
│   ├── llm.py                    # Anthropic tool-use loop
│   ├── mcp_client.py             # MCP session; tool bridge
│   ├── models.py                 # ResearchSource, ResearchResults, Report
│   ├── agents/
│   │   └── researcher.py         # LLM-driven web research
│   └── mcp_server/               # standalone MCP tool server (fetch_url)
└── tests/                        # pytest suite
```
