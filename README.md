# agent-orchestration-mcp

`maestro` is a multi-agent system that researches a prompt and writes a cited report, using
LLMs, agents, and the Model Context Protocol (MCP).

> **Status:** early development. The orchestration entry point is in place and currently
> returns an empty report; agents and tools are added one tested behavior at a time. API keys
> are introduced only when a step requires them.

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
```

This creates a project-local virtual environment in `.venv/` and installs dependencies.

## Usage

Activate the environment, then run the CLI:

```bash
source .venv/bin/activate

maestro "What are the trade-offs of MCP versus plain function calling?"
# equivalently:
python -m maestro "What are the trade-offs of MCP versus plain function calling?"
```

Or run without activating: `uv run maestro "..."`.

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
├── .pre-commit-config.yaml       # ruff lint/format on commit
├── .github/workflows/ci.yml      # lint + test on each PR
├── src/maestro/
│   ├── __main__.py               # enables `python -m maestro`
│   ├── cli.py                    # command-line entry point
│   ├── orchestrator.py           # coordinates the agent pipeline
│   ├── models.py                 # shared data types (Report, ...)
│   └── mcp_server/               # standalone MCP tool server (fetch_url)
└── tests/                        # pytest suite
```
