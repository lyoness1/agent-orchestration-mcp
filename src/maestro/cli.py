"""Command-line entry point."""

import argparse
import asyncio

from maestro.constants import load_env
from maestro.orchestrator import Orchestrator

# Used when the CLI is invoked with no question, so `maestro` alone still runs.
DEFAULT_QUESTION = "What is the Model Context Protocol?"


def _parse_question(argv: list[str] | None) -> str:
    """Parse CLI arguments and return the question to research.

    ``argv`` defaults to None (argparse then reads ``sys.argv``); tests pass a
    list directly so they never have to mutate global state.
    """
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Research a question with a pipeline of agents and print a report.",
    )
    # nargs="*" lets the question be typed unquoted (multiple words) and also
    # allows zero args, which we handle with a fallback instead of erroring.
    parser.add_argument(
        "question",
        nargs="*",
        help="the question to research (falls back to a default if omitted)",
    )
    args = parser.parse_args(argv)
    return " ".join(args.question) or DEFAULT_QUESTION


def main(argv: list[str] | None = None) -> int:
    """Run the CLI: research the question, print the report, return an exit code."""
    load_env()
    question = _parse_question(argv)
    # asyncio.run is the single sync -> async boundary: the CLI stays synchronous
    # while the orchestrator and everything it awaits are async.
    report = asyncio.run(Orchestrator().run(question))
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
