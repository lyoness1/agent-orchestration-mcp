# agent-orchestration-mcp

`maestro` is a multi-agent system that researches a prompt and writes a cited report, using
LLMs, agents, and the Model Context Protocol (MCP).

> **Status:** Researcher agent with live Anthropic tool-use loop. Copy `.env.example` to
> `.env` for local configuration; settings load automatically when the process starts.

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

## Configuration

Settings live in `src/maestro/settings.py`:

- A `Settings` dataclass defines defaults (API key, LLM model/token limits, MCP fetch limits).
- `load_settings()` merges a project-root `.env` file over those defaults when the module is first imported.
- The module exports a singleton: `settings = load_settings()`.

Precedence: **`.env` > dataclass defaults**. Numeric values in `.env` are coerced to match
the field type (`int` / `float` / `str`). See `.env.example` for available keys.

Application code imports the singleton directly:

```python
from maestro.settings import settings

api_key = settings.ANTHROPIC_API_KEY
```

Each process loads its own settings snapshot — for example, `maestro` and the separate
`maestro-mcp` server each read `.env` at startup.

Tests patch `settings` on each module that imported it (see `tests/conftest.py`).

## Usage

Activate the environment, then run the CLI:

```bash
source .venv/bin/activate

maestro "What are the trade-offs of MCP versus plain function calling?"
# equivalently:
python -m maestro "What are the trade-offs of MCP versus plain function calling?"
```

Or run without activating: `uv run maestro "..."`.

If `ANTHROPIC_API_KEY` is unset, the run fails early with `MissingApiKeyError`.

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
