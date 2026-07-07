"""Researcher agent: answers a question with an LLM-driven web tool loop.

The researcher hands the question and the MCP server's tools to the model, then
lets the model decide which pages to fetch. It owns the research prompt and the
wiring between the LLM's tool requests and the MCP client; the loop mechanics
live in ``maestro.llm``.
"""

from __future__ import annotations

from typing import Any

from maestro.llm import LlmClient
from maestro.mcp_client import MaestroMcpClient

SYSTEM_PROMPT = (
    "You are a meticulous research agent. Answer the user's question using the "
    "web tools available to you. Fetch real pages to gather evidence before you "
    "answer, prefer primary and authoritative sources, and never invent facts or "
    "URLs. If a tool returns an error, try a different source rather than giving "
    "up. When you have enough evidence, write a concise, well-structured answer "
    "and list the URLs you relied on."
)


async def research(question: str, mcp: MaestroMcpClient, llm: LlmClient) -> str:
    """Research ``question`` with the model driving MCP tools, and return its answer."""
    tools = await mcp.anthropic_tools()

    async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
        return await mcp.call_tool(name, arguments)

    return await llm.run_tool_loop(
        system=SYSTEM_PROMPT,
        prompt=question,
        tools=tools,
        execute_tool=execute_tool,
    )
