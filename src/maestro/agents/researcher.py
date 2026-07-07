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
    """Execute ``plan`` using the Anthropic tool-use pattern.

    For each plan item we call client.messages.create in a loop until the model
    stops (end_turn). When the model requests fetch_url, we run MCP, append the
    page text to the conversation, and ask again. Sources are saved in our code; the
    model's final text becomes the report answer until Analyst/Editor exist.
    """
    sources: list[Source] = []
    answers: list[str] = []
    tools = [FETCH_URL_TOOL]

    for item in plan.items:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Research this subtopic: {item.subtopic}"},
        ]

        for _turn in range(MAX_TOOL_TURNS):
            response = llm.create_message(
                system=RESEARCH_SYSTEM,
                messages=messages,
                tools=tools,
            )

            if response.stop_reason == "end_turn":
                if text := response.text():
                    answers.append(text)
                break

            if response.stop_reason != "tool_use":
                msg = f"Unexpected stop_reason: {response.stop_reason}"
                raise RuntimeError(msg)

            tool_results: list[dict[str, Any]] = []
            for request in response.tool_use_requests():
                output = await _run_fetch_url(request, mcp, sources)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": request["id"],
                        "content": output,
                    }
                )

            messages.append({"role": "assistant", "content": list(response.content)})
            messages.append({"role": "user", "content": tool_results})
        else:
            msg = f"Tool conversation exceeded {MAX_TOOL_TURNS} turns for subtopic: {item.subtopic}"
            raise RuntimeError(msg)

    return ResearchSources(
        question=plan.question,
        sources=tuple(sources),
        answer="\n\n".join(answers),
    )


async def _run_fetch_url(
    request: dict[str, Any],
    mcp: MaestroMcpClient,
    sources: list[Source],
) -> str:
    """Run one fetch_url tool call from the model and record a Source."""
    if request["name"] != "fetch_url":
        return f"Unknown tool: {request['name']}"

    url = str(request["input"].get("url", ""))
    page_text = await mcp.fetch_url(url)
    sources.append(
        Source(
            citation_key=f"ref-{len(sources) + 1}",
            url=url,
            excerpt=page_text,
            tool="fetch_url",
        )
    )
    return page_text
