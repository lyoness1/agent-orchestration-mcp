"""Command-line entry point."""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

from maestro.orchestrator import Orchestrator

# Used when the CLI is invoked with no question, so `maestro` alone still runs.
DEFAULT_QUESTION = "What is the Model Context Protocol?"


@dataclass(frozen=True)
class CliArgs:
    question: str
    live: bool


def _parse_args(argv: list[str] | None) -> CliArgs:
    """Parse CLI arguments.

    ``argv`` defaults to None (argparse then reads ``sys.argv``); tests pass a
    list directly so they never have to mutate global state.
    """
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Research a question with a pipeline of agents and print a report.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="call the Anthropic API instead of replaying local mock responses",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="the question to research (falls back to a default if omitted)",
    )
    args = parser.parse_args(argv)
    question = " ".join(args.question) or DEFAULT_QUESTION
    return CliArgs(question=question, live=args.live)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI: research the question, print the report, return an exit code."""
    cli_args = _parse_args(argv)
    if cli_args.live and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY is required when using --live. Set it in the environment or .env.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    report = asyncio.run(Orchestrator(live=cli_args.live).run(cli_args.question))
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
