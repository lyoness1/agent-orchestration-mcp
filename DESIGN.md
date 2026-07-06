# Design

Maestro is a multi-agent orchestration system that coordinates specialized agents  
over the Model Context Protocol (MCP), backed by the Anthropic API. It takes a  
research question, gathers live web evidence through MCP tools, and produces a  
cited report.

## Process model

v1 runs two local processes plus one remote service:

1. **Application process** — the orchestrator and agents. It acts as the MCP
  *client* and calls the Anthropic API.
2. **MCP server process** — `maestro-mcp`, exposing web-research tools
  (`fetch_url`, `web_search`). It runs as a separate process.
3. **Anthropic API** — a remote service, not a process managed by this project.

Agents (Planner, Researcher, Analyst, Editor) are roles within the single
application process, not separate processes. Process count scales with the
number of MCP servers, not the number of agents.

```mermaid
flowchart TD
    subgraph app["Process 1: application (maestro)"]
        ORC["Orchestrator"]
        P["Planner"]
        R["Researcher"]
        A["Analyst"]
        E["Editor"]
        MC["MCP client"]
        ORC --> P --> R --> A --> E
        R -.uses.-> MC
    end

    subgraph srv["Process 2: MCP server (maestro-mcp)"]
        T1["fetch_url"]
        T2["web_search"]
    end

    API["Anthropic API (remote)"]

    MC <-->|"MCP protocol (stdio)"| srv
    P <-->|messages| API
    R <-->|messages + tool use| API
    A <-->|messages| API
    E <-->|messages| API
    T1 --> WEB["Public web"]
    T2 --> WEB
```



The process diagram shows Planner with an API path to reflect the target
architecture; in v1 the Planner is a stub that does not call the API (see
[Planner in v1](#planner-in-v1)).

## MCP concepts

- **Server** — exposes tools (and optionally resources or prompts). It is launched
as its own process and is client-agnostic.
- **Client** — connects to a server, lists its tools, and invokes them on behalf
of agents.
- **Tools** — named, schema-described functions the model can call (e.g.
`fetch_url`, `web_search`).
- **Transport** — how client and server exchange JSON-RPC messages.



### Transport: stdio (v1)

The client launches the server as a subprocess and communicates over
stdin/stdout. Lifecycle is tied to the client; the relationship is 1:1; no
ports or authentication.

MCP client code is isolated behind a thin wrapper so the transport can be
swapped without changing agent or orchestrator code.

### Tool integration: MCP client and the Researcher

The Researcher is the only agent that uses MCP tools. Two patterns connect MCP
to the Researcher:

1. **Direct invocation** — Python code calls `mcp_client.invoke("fetch_url", …)`
  based on a fixed plan. No LLM in the tool-selection loop.
2. **Bridged tool-use loop** — The MCP client lists tools from the server and
  exposes them as Anthropic tool definitions. The Researcher runs the Anthropic
   messages API with `tools=…`. When the model returns a `tool_use` block, the
   client executes it via MCP and returns a `tool_result`; the loop continues
   until the model finishes.

**Chosen: bridged tool-use loop for the Researcher.** This matches the standard
pattern for LLM agents with external tools: the model decides *when* and *which*
tool to call; the client executes via MCP. The MCP client owns schema conversion
(MCP → Anthropic) and tool dispatch. Direct `mcp_client.invoke` remains available
for integration tests and debugging without an LLM.

```mermaid
sequenceDiagram
    participant R as Researcher (LLM loop)
    participant API as Anthropic API
    participant MC as MCP client
    participant S as maestro-mcp

    R->>API: messages + tools (from MCP schemas)
    API-->>R: tool_use (e.g. fetch_url)
    R->>MC: execute tool call
    MC->>S: MCP invoke fetch_url
    S-->>MC: text result
    MC-->>R: tool_result
    R->>API: continue until stop
    R-->>R: emit ResearchSources
```



See [Tool execution: direct vs bridged loop](#tool-execution-direct-vs-bridged-loop)
for the full tradeoff analysis.

## Agent roles

Four specialized roles form a sequential pipeline. Each role has a distinct
responsibility so prompts, tests, and failure modes stay narrow.


| Role           | Responsibility                                                                                                         | Tools                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **Planner**    | Turn the user question into a structured research plan: subtopics, candidate URLs, and questions to answer.            | None (LLM only)                                           |
| **Researcher** | Execute the plan: call MCP tools to fetch pages and search the web; collect raw sources with metadata.                 | MCP `fetch_url`, `web_search` (via bridged tool-use loop) |
| **Analyst**    | Synthesize sources into findings: claims, evidence, and citation keys. Output is structured analysis, not final prose. | None (LLM only)                                           |
| **Editor**     | Turn analysis into the final `Report`: readable markdown with inline citations and a bibliography.                     | None (LLM only)                                           |




### Why Editor is separate from Analyst

The Analyst optimizes for *correctness and traceability*: mapping claims to
sources, resolving conflicts, and flagging gaps. The Editor optimizes for
*readability and citation format*: tone, structure, and consistent reference
style. Merging them would couple two different quality bars and make it harder
to test synthesis independently of presentation. The Analyst output is also
useful as an intermediate artifact (e.g. for debugging or alternate renderings)
without re-running research.

### Planner in v1

The Planner role exists in the architecture from the start, but v1 implements it
as a **stub**: wrap the user question in a single-item `ResearchPlan` with no LLM
call. The module boundary and artifact shape are stable so a real LLM-backed
Planner (subtopic decomposition, fan-out) can replace the stub without changing
downstream agents.

```python
# v1 stub — replace with LLM call when fan-out Planner is implemented
def plan(question: str) -> ResearchPlan:
    return ResearchPlan(question=question, items=(PlanItem(subtopic=question),))
```



## Pipeline data model

Agents communicate through **typed, immutable artifacts** defined in
`src/maestro/models.py`. Each handoff has one input and one output type so
boundaries are testable and prompts stay focused. Field names below are
illustrative; exact types are implemented with frozen dataclasses.

```mermaid
flowchart LR
    Q["question: str"] --> RP["ResearchPlan"]
    RP --> RS["ResearchSources"]
    RS --> AN["Analysis"]
    AN --> REP["Report"]
```





### Handoff summary


| Artifact       | Producer   | Consumer     | Purpose                                         |
| -------------- | ---------- | ------------ | ----------------------------------------------- |
| `ResearchPlan` | Planner    | Researcher   | What to research: subtopics, queries, seed URLs |
| `ResearchSources` | Researcher | Analyst      | Raw evidence retrieved from the web             |
| `Analysis`     | Analyst    | Editor       | Structured findings with citation keys          |
| `Report`       | Editor     | CLI / caller | Final human-readable cited output               |




### `ResearchPlan`

**Purpose:** Decompose the user question into actionable research work.


| Field      | Type                 | Description                            |
| ---------- | -------------------- | -------------------------------------- |
| `question` | `str`                | Original user question                 |
| `items`    | `tuple[PlanItem, …]` | One or more research tasks (one in v1) |


`PlanItem`


| Field            | Type            | Description                                        |
| ---------------- | --------------- | -------------------------------------------------- |
| `subtopic`       | `str`           | Focus area to investigate                          |
| `search_queries` | `tuple[str, …]` | Suggested web search queries (optional in v1 stub) |
| `seed_urls`      | `tuple[str, …]` | URLs to fetch directly (optional)                  |




### `ResearchSources`

**Purpose:** Collected web evidence before synthesis. Fan-in merges multiple
Researcher outputs into one `ResearchSources` for the Analyst.


| Field      | Type               | Description                     |
| ---------- | ------------------ | ------------------------------- |
| `question` | `str`              | Original question (for context) |
| `sources`  | `tuple[Source, …]` | Retrieved documents             |


`Source`


| Field          | Type  | Description                                          |
| -------------- | ----- | ---------------------------------------------------- |
| `citation_key` | `str` | Stable id for references (e.g. `ref-1`)              |
| `url`          | `str` | Source URL                                           |
| `excerpt`      | `str` | Text returned by the tool (possibly truncated)       |
| `tool`         | `str` | Which tool produced this (`fetch_url`, `web_search`) |

`title` is omitted until `fetch_url` returns page metadata.




### `Analysis`

**Purpose:** Synthesized findings with traceability to sources. Not final prose.


| Field      | Type                | Description                               |
| ---------- | ------------------- | ----------------------------------------- |
| `question` | `str`               | Original question                         |
| `findings` | `tuple[Finding, …]` | Claims supported by evidence              |
| `gaps`     | `tuple[str, …]`     | What could not be verified or was missing |


`Finding`


| Field           | Type            | Description                           |
| --------------- | --------------- | ------------------------------------- |
| `claim`         | `str`           | A single synthesized statement        |
| `citation_keys` | `tuple[str, …]` | References into `Source.citation_key` |




### `Report`

**Purpose:** Final output shown to the user. Already defined in `models.py`.


| Field      | Type            | Description                                   |
| ---------- | --------------- | --------------------------------------------- |
| `question` | `str`           | Original question                             |
| `summary`  | `str`           | Narrative answer with inline citations        |
| `sources`  | `tuple[str, …]` | Bibliography entries (URLs or formatted refs) |




## Orchestration: fan-out / fan-in

The orchestrator decomposes the question, dispatches research workers, then
synthesizes and formats the result.

```mermaid
flowchart LR
    Q["Question"] --> P["Planner"]
    P --> R1["Researcher 1"]
    P -.-> R2["Researcher 2"]
    P -.-> Rn["Researcher N"]
    R1 --> A["Analyst (fan-in)"]
    R2 -.-> A
    Rn -.-> A
    A --> E["Editor"]
    E --> OUT["Cited Report"]
```



In v1 the Planner stub lives in the orchestrator (`stub_research_plan`): it emits
a single `PlanItem` and one Researcher runs; the diagram structure is unchanged
when fanning out to N researchers.

## Components and repository structure

Package layout uses the `src/maestro/` convention (installed via `uv`). The MCP
server must not import orchestration code; dependency direction is one-way
(application → server, via the protocol).

```
agent-orchestration-mcp/
├── pyproject.toml
├── DESIGN.md
├── src/maestro/
│   ├── __main__.py              # `python -m maestro`
│   ├── cli.py                   # CLI entry point
│   ├── orchestrator.py          # wires the agent pipeline
│   ├── constants.py             # shared constants (e.g. probe URLs in dev)
│   ├── models.py                # pipeline artifacts + Report
│   ├── mcp_client.py            # MCP session, tool bridge, invoke
│   ├── llm.py                   # Anthropic client + tool-use loop
│   ├── agents/                  # one module per role
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── analyst.py
│   │   └── editor.py
│   └── mcp_server/              # standalone MCP tool server
│       ├── server.py            # FastMCP entry (`maestro-mcp`)
│       ├── fetch_url.py
│       └── web_search.py
└── tests/
```


| Component    | Path                          | Role                                                        |
| ------------ | ----------------------------- | ----------------------------------------------------------- |
| CLI          | `src/maestro/cli.py`          | Parses a question, runs the orchestrator, prints the report |
| Orchestrator | `src/maestro/orchestrator.py` | Coordinates the agent pipeline                              |
| Models       | `src/maestro/models.py`       | Shared pipeline artifacts                                   |
| MCP server   | `src/maestro/mcp_server/`     | Standalone tool server (`maestro-mcp`)                      |
| MCP client   | `src/maestro/mcp_client.py`   | Spawns the server, bridges tools to Anthropic               |
| LLM helper   | `src/maestro/llm.py`          | Anthropic API and tool-use loop                             |
| Agents       | `src/maestro/agents/`         | One module per pipeline role                                |




## Tooling

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`,
`uv.lock`).


| Dependency        | Role                                              |
| ----------------- | ------------------------------------------------- |
| **mcp**           | Official MCP SDK (FastMCP server; client session) |
| **httpx**         | HTTP client for `fetch_url`                       |
| **Anthropic SDK** | LLM calls and tool-use loop                       |


Search and richer page-extraction libraries are introduced when the
corresponding tools are built.

## Architecture tradeoffs

For each decision below, the chosen option reflects v1 priorities: a small,
testable surface area, clear process boundaries, and a pipeline that can grow
to parallel research without restructuring.

### MCP transport: stdio vs Streamable HTTP


|               | stdio                                       | Streamable HTTP                            |
| ------------- | ------------------------------------------- | ------------------------------------------ |
| **Lifecycle** | Client spawns server as subprocess          | Server runs independently on a URL         |
| **Coupling**  | 1:1 client–server                           | Many clients can share one server          |
| **Ops**       | No ports, no auth on the tool server        | Requires network surface, auth, deployment |
| **Fit**       | Local dev, single application driving tools | Remote or shared tool servers              |


**Chosen: stdio.** v1 has one application process driving one tool server.
Subprocess lifecycle is automatic, there is no extra network attack surface, and
the MCP client wrapper can swap transports later without touching agents.

### MCP server: separate process vs in-process library


|              | Separate process                             | In-process import                       |
| ------------ | -------------------------------------------- | --------------------------------------- |
| **Boundary** | Protocol-enforced; server is client-agnostic | Shared memory; tighter coupling         |
| **Testing**  | Server and tools testable without the LLM    | Simpler call path, fewer moving parts   |
| **Reuse**    | Any MCP client can use the tools             | Only this application can use the tools |


**Chosen: separate process.** MCP’s value is a standard tool boundary. A
standalone server matches how MCP clients (including this app) integrate in
production and keeps HTTP/search logic out of the agent process.

### Tool execution: direct vs bridged loop


|                              | Direct MCP invocation         | Bridged Anthropic tool-use loop                |
| ---------------------------- | ----------------------------- | ---------------------------------------------- |
| **Who picks tools**          | Python code (plan-driven)     | LLM during Researcher turn                     |
| **Complexity**               | Low; easy to test without API | Higher; needs loop, schema bridge, `max_turns` |
| **Flexibility**              | Fixed execution path          | Model can adapt (extra fetches, follow links)  |
| **Fidelity to MCP + agents** | Tests MCP only                | Exercises full agent + MCP stack               |


**Chosen: bridged loop for the Researcher runtime path.** Direct
`mcp_client.invoke` is still used in MCP client tests and debugging. The
Researcher uses the Anthropic tool-use loop with MCP tools bridged to Anthropic
schemas — the standard pattern for tool-using LLM agents.

### Agent count: four roles vs three


|                      | Four roles (Planner, Researcher, Analyst, Editor) | Three roles (merge Planner and/or Editor)      |
| -------------------- | ------------------------------------------------- | ---------------------------------------------- |
| **Planner separate** | Stable interface for fan-out to N subtopics       | Orchestrator owns decomposition; fewer modules |
| **Editor separate**  | Synthesis and presentation tested independently   | Analyst produces final prose; fewer LLM calls  |
| **Complexity**       | More modules and prompts                          | Fewer boundaries                               |


**Chosen: four roles.** Planner and Editor are thin in v1 but their boundaries
match the fan-out/fan-in shape the orchestrator will grow into. Separating
Analyst (evidence) from Editor (prose and citations) keeps two different
quality bars from colliding in one prompt.

### Orchestration: hand-rolled loop vs framework (e.g. LangGraph)


|                 | Hand-rolled async pipeline                     | Graph framework                           |
| --------------- | ---------------------------------------------- | ----------------------------------------- |
| **Visibility**  | Linear code; straightforward to read in review | Declarative graph; more abstraction       |
| **Flexibility** | Full control over state passing                | Branching, checkpoints, human-in-the-loop |
| **Cost**        | More boilerplate for complex flows             | Learning curve and dependency             |


**Chosen: hand-rolled loop for v1.** The v1 pipeline is sequential with a
fixed shape. A graph framework pays off when branching, retries, or parallel
fan-out become central; the design leaves room to adopt one later without
changing agent interfaces.

### Research fan-out: sequential vs parallel (v1)


|                 | One Researcher (v1)                      | N parallel Researchers                       |
| --------------- | ---------------------------------------- | -------------------------------------------- |
| **Concurrency** | Simple; one MCP session                  | Requires session-per-worker or shared server |
| **Validation**  | End-to-end path with fewer failure modes | Higher throughput for broad questions        |
| **State**       | Linear handoff between agents            | Fan-in merge at Analyst                      |


**Chosen: sequential in v1.** Parallel fan-out is a first-class part of the
architecture (see orchestration diagram) but deferred until the MCP client,
agents, and Analyst fan-in are proven with a single worker.

### Web search provider: Tavily vs DuckDuckGo (and similar)


|                 | Tavily (or similar API)                | DuckDuckGo / no-key fallback        |
| --------------- | -------------------------------------- | ----------------------------------- |
| **Results**     | Structured snippets suited to tool use | Less structure; more parsing burden |
| **Setup**       | API key required                       | No key; good for local dev          |
| **Reliability** | Paid SLA                               | Best-effort scraping                |


**Open for v1 implementation.** The MCP `web_search` tool will pick one
primary backend with a documented fallback strategy. Tavily favors result
quality; a no-key option favors zero-config development.

## v1 scope and future options

**v1 delivers:** a sequential pipeline (Planner stub → one Researcher with
bridged tool-use loop → Analyst → Editor), stdio MCP transport, `fetch_url` and
`web_search` tools, hand-rolled Anthropic tool-use loop, and a cited `Report` on
the CLI.

**Next slice (logging):** verbose pipeline progress via `maestro -v` is specified
on branch **`docs/logging-slice`** (see that branch's `DESIGN.md` for incremental
slices and logging conventions).

**Future options worth revisiting** (not commitments):

- **Streamable HTTP** for MCP when remote or shared tool servers are needed.
- **Parallel Researchers** via `asyncio` fan-out from the Planner, with
independent MCP client sessions per worker.
- **LangGraph (or similar)** if branching, checkpoints, or human-in-the-loop
review become requirements.
- **Richer page extraction** (e.g. trafilatura) if regex-based HTML stripping
proves insufficient for target sites.
- **Planner depth** — replace the v1 stub with an LLM-backed decomposition when
fan-out is enabled.



## Operational constraints

- Secrets in `.env`, never committed.
- A `max_turns` bound on the tool-use loop to cap cost and prevent runaway runs.
- The MCP server is runnable and testable independently of the LLM.
- Tool descriptions are part of the prompt surface; keep them precise.
- Tool failures surface useful messages to the model rather than aborting the run.
- Web tools fetch arbitrary URLs; apply request timeouts and treat user-supplied
URLs as untrusted input (SSRF and abuse risks are acknowledged; hardening is
incremental).



## Testing

Testing follows the same boundaries as the architecture: each layer is verified
in isolation before the full pipeline.


| Layer            | What is tested                                  | How                                                   |
| ---------------- | ----------------------------------------------- | ----------------------------------------------------- |
| **MCP tools**    | `fetch_url`, `web_search` behavior              | Unit tests with HTTP/search APIs mocked; no LLM       |
| **MCP server**   | Tool registration and protocol                  | Unit tests; optional subprocess smoke test            |
| **MCP client**   | Spawn server, list tools, invoke, schema bridge | Integration tests with real subprocess or test double |
| **Agents**       | Each role’s input → output artifact             | Tests with LLM responses mocked                       |
| **Orchestrator** | Full pipeline handoffs                          | End-to-end test with mocked LLM and mocked HTTP       |
| **CLI**          | Argument parsing and output                     | `pytest` with captured stdout                         |


New behavior is added test-first: a failing test for the slice, then the minimal
implementation to pass. Continuous integration runs `ruff check`, `ruff format --check`, and `pytest` on every pull request.