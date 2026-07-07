"""Orchestrator tests.

The orchestrator now drives a live Anthropic tool-use loop, so the end-to-end
test is not mocked: it is skipped unless a real API key is present and hits the
network when it runs.
"""

import asyncio
import os

import pytest

from maestro.llm import API_KEY_ENV
from maestro.models import Report
from maestro.orchestrator import Orchestrator

requires_api_key = pytest.mark.skipif(
    not os.environ.get(API_KEY_ENV),
    reason=f"{API_KEY_ENV} not set; live Anthropic API and network required",
)


@requires_api_key
def test_run_researches_question_live() -> None:
    report = asyncio.run(Orchestrator().run("What is the Model Context Protocol?"))

    assert isinstance(report, Report)
    assert report.question == "What is the Model Context Protocol?"
    assert report.summary.strip()
