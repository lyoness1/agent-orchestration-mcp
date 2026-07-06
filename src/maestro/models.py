"""Core data types shared across the pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanItem:
    """One piece of research work the Researcher should execute."""

    subtopic: str  # Focus area to investigate (may differ from the original question)
    search_queries: tuple[str, ...] = ()  # Suggested web searches (Planner fills these later)
    seed_urls: tuple[str, ...] = ()  # URLs to fetch directly (Planner fills these later)


@dataclass(frozen=True)
class ResearchPlan:
    """What to research: produced by Planner, consumed by Researcher.

    Carries the original question for context plus one or more plan items.
    v1 stub plans have a single item; fan-out plans have many.
    """

    question: str
    items: tuple[PlanItem, ...]


@dataclass(frozen=True)
class Source:
    """One web document retrieved during research."""

    citation_key: str  # Short stable id for inline refs, e.g. "ref-1" → [ref-1] in the report
    url: str
    excerpt: str  # Text returned by fetch_url or web_search (may be truncated)
    tool: str  # MCP tool that produced this, e.g. "fetch_url"


@dataclass(frozen=True)
class ResearchSources:
    """Raw web evidence collected for a question.

    Researcher output; Analyst input. When the orchestrator fans out to multiple
    Researcher passes, their results merge into one ResearchSources before Analyst.
    """

    question: str
    sources: tuple[Source, ...]
    answer: str = ""  # Model's final text after fetching (until Analyst synthesizes)


@dataclass(frozen=True)
class Report:
    """The result of a run for a single question.

    ``frozen=True`` blocks reassigning fields (e.g. ``report.summary = ...``),
    which helps prevent one agent from clobbering another agent's results.
    """

    question: str
    summary: str = ""  # Answer shown to the user (model prose until Editor refines it)
    # A tuple is immutable, which matches frozen=True: unlike a list it can't be
    # mutated in place (no .append), so a Report is genuinely read-only. An empty
    # tuple is a safe default and needs no default_factory.
    sources: tuple[str, ...] = ()

    def render(self) -> str:
        """Return a human-readable, multi-line view of the report."""
        answer = self.summary or "(no answer yet)"
        lines = [f"Question: {self.question}", "", "Answer:", answer, ""]
        if self.sources:
            lines.append("Sources:")
            lines.extend(f"  {entry}" for entry in self.sources)
        else:
            lines.append("Sources:")
            lines.append("  (none)")
        return "\n".join(lines)
