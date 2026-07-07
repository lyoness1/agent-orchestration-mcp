"""Core data types shared across the pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchSource:
    """One page or tool result gathered during a research pass."""

    url: str
    excerpt: str
    tool: str


@dataclass(frozen=True)
class ResearchResults:
    """Output of a Researcher run: gathered sources and the model's answer."""

    sources: tuple[ResearchSource, ...]
    answer: str


@dataclass(frozen=True)
class Report:
    """The result of a run for a single question.

    ``frozen=True`` blocks reassigning fields (e.g. ``report.summary = ...``),
    which helps prevent one agent from clobbering another agent's results.
    """

    question: str
    summary: str = ""
    # A tuple is immutable, which matches frozen=True: unlike a list it can't be
    # mutated in place (no .append), so a Report is genuinely read-only. An empty
    # tuple is a safe default and needs no default_factory.
    sources: tuple[str, ...] = ()

    def render(self) -> str:
        """Return a human-readable, multi-line view of the report."""
        summary = self.summary or "(no summary yet)"
        sources = "\n".join(f"- {source}" for source in self.sources) or "(none yet)"
        return f"Question: {self.question}\n\nSummary: {summary}\n\nSources:\n{sources}"
