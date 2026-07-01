"""Coordinates the agent pipeline that answers a question."""

from maestro.models import Report


class Orchestrator:
    """Runs the agent pipeline end to end.

    Returns an empty report for now. The planner, researcher, analyst, and
    editor agents are added one tested behavior at a time in later steps.
    """

    # `run` is async even though the body currently does no I/O: the real
    # pipeline will `await` the LLM and MCP tool calls. Committing to async now
    # avoids having to change this signature and every caller later.
    async def run(self, question: str) -> Report:
        """Answer ``question`` and return the resulting Report."""
        return Report(question=question)
