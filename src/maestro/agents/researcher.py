"""Researcher: gathers web evidence for a question via MCP tools."""

from __future__ import annotations

from typing import Any

from maestro.llm import FETCH_URL_TOOL, LlmClient
from maestro.mcp_client import MaestroMcpClient
from maestro.models import ResearchPlan, ResearchSources, Source

# System prompt: who the model is for this agent (separate from the user's question).
RESEARCH_SYSTEM = (
    "You are a research assistant. Use fetch_url to retrieve web pages relevant to "
    "the subtopic. Fetch at least one useful page before finishing."
)

MAX_TOOL_TURNS = 8


async def research(plan: ResearchPlan, mcp: MaestroMcpClient, llm: LlmClient) -> ResearchSources:
    """Execute ``plan`` with the Anthropic tool-use loop.

    For each plan item, call the model until it stops (end_turn). When the model
    requests fetch_url, run MCP, record a Source, and feed the page text back as a
    tool_result. Sources and answers accumulate across all plan items into one
    ResearchSources: v1 runs a single Researcher over every subtopic sequentially;
    parallel fan-out across Researchers is future work.
    """
    sources: list[Source] = []
    answers: list[str] = []

    for item in plan.items:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Research this subtopic: {item.subtopic}"},
        ]

        for _turn in range(MAX_TOOL_TURNS):
            response = llm.create_message(
                system=RESEARCH_SYSTEM, messages=messages, tools=[FETCH_URL_TOOL]
            )

            if response.stop_reason == "end_turn":
                if answer := response.text():
                    answers.append(answer)
                break

            if response.stop_reason != "tool_use":
                raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

            tool_results: list[dict[str, Any]] = []
            for request in response.tool_use_requests():
                url = str(request["input"].get("url", ""))
                page_text = await mcp.fetch_url(url)
                # TODO: Truncate/summarize page_text before sending it back on live
                # runs — full pages inflate token cost. Keep the full text in
                # Source.excerpt for the report bibliography.
                sources.append(
                    Source(
                        citation_key=f"ref-{len(sources) + 1}",
                        url=url,
                        excerpt=page_text,
                        tool="fetch_url",
                    )
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": request["id"], "content": page_text}
                )

            messages.append({"role": "assistant", "content": list(response.content)})
            messages.append({"role": "user", "content": tool_results})
        else:
            raise RuntimeError(
                f"Tool conversation exceeded {MAX_TOOL_TURNS} turns for subtopic: {item.subtopic}"
            )

    return ResearchSources(
        question=plan.question, sources=tuple(sources), answer="\n\n".join(answers)
    )
