"""Researcher agent: answers a question with an LLM-driven web tool loop.

The researcher hands the question and the MCP server's tools to the model, then
lets the model decide which pages to fetch. It owns the research prompt and the
wiring between the LLM's tool requests and the MCP client; the loop mechanics
live in ``maestro.llm``.

When the Planner exists the signature becomes ``research(question, task, mcp, llm)``
and ``task.focus`` drives the prompt; the orchestrator fans out one call per task.
"""

from __future__ import annotations

from typing import Any

from maestro.llm import LlmClient
from maestro.mcp_client import MaestroMcpClient
from maestro.models import ResearchResults, ResearchSource

SYSTEM_PROMPT = (
    "You are a meticulous research agent. Answer the user's question using the "
    "web tools available to you. Fetch real pages to gather evidence before you "
    "answer, prefer primary and authoritative sources, and never invent facts or "
    "URLs. If a tool returns an error, try a different source rather than giving "
    "up. When you have enough evidence, write a concise, well-structured answer "
    "and list the URLs you relied on."
)


async def research(question: str, mcp: MaestroMcpClient, llm: LlmClient) -> ResearchResults:
    """Research ``question`` with the model driving MCP tools.

    Returns gathered sources (captured from tool calls) and the model's answer.
    When the Planner lands, this gains a ``task: ResearchTask`` argument and uses
    ``task.focus`` as the research prompt instead of the full question.
    """
    tools = await mcp.anthropic_tools()
    sources: list[ResearchSource] = []

    async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
        result = await mcp.call_tool(name, arguments)
        sources.append(
            ResearchSource(
                url=str(arguments.get("url", "")),
                excerpt=result,
                tool=name,
            )
        )
        return result

    answer = await llm.run_tool_loop(
        system=SYSTEM_PROMPT,
        prompt=question,
        tools=tools,
        execute_tool=execute_tool,
    )
    return ResearchResults(sources=tuple(sources), answer=answer)
