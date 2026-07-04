"""Researcher: gathers web evidence for a question via MCP tools."""

from __future__ import annotations

from maestro.constants import PROBE_URL
from maestro.mcp_client import MaestroMcpClient
from maestro.models import ResearchPlan, ResearchSources, Source


async def research(plan: ResearchPlan, mcp: MaestroMcpClient) -> ResearchSources:
    """Execute ``plan`` using MCP tools and return collected sources.

    Reads ``plan.items`` to decide what to fetch (subtopic, seed URLs, search
    queries). v1 stub ignores item fields and always fetches a fixed probe page;
    later steps use seed URLs and an LLM-driven tool-use loop.
    """
    sources: list[Source] = []
    for _item in plan.items:
        page_text = await mcp.fetch_url(PROBE_URL)
        sources.append(
            Source(
                citation_key=f"ref-{len(sources) + 1}",
                url=PROBE_URL,
                excerpt=page_text,
                tool="fetch_url",
            )
        )
    return ResearchSources(question=plan.question, sources=tuple(sources))
