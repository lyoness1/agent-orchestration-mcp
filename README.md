# agent-orchestration-mcp

`maestro` is a multi-agent system that researches a prompt and writes a cited report, using
LLMs, agents, and the Model Context Protocol (MCP).

> **Status:** early development. The orchestration entry point is in place and currently
> returns an empty report; agents and tools are added one tested behavior at a time. API keys
> are introduced only when a step requires them.

## Architecture

- **Orchestrator** — runs a pipeline of specialized agents (planner → researcher → analyst →
  editor). Agents are roles within a single application process.
- **MCP tool server** — a standalone process exposing web-research tools; the application
  connects to it as an MCP client.
- **LLM** — the Anthropic API powers the agents and the tool-use loop.

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

```
agent-orchestration-mcp/
├── pyproject.toml                # project metadata, dependencies, tooling config
├── .pre-commit-config.yaml       # ruff lint/format on commit
├── .github/workflows/ci.yml      # lint + test on each PR
├── src/maestro/
│   ├── __main__.py               # enables `python -m maestro`
│   ├── cli.py                    # command-line entry point
│   ├── orchestrator.py           # coordinates the agent pipeline
│   └── models.py                 # shared data types (Report, ...)
└── tests/                        # pytest suite
```
