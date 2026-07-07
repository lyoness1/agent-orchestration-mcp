"""Shared pytest configuration and autouse fixtures."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import AbstractAsyncContextManager
from unittest.mock import MagicMock, patch

import pytest

from maestro.mcp_client import MaestroMcpClient
from mcp_test_helpers import DEFAULT_PAGE_TEXT, in_process_mcp_session, mock_response

McpClientFactory = Callable[[], AbstractAsyncContextManager[MaestroMcpClient]]

# Default URL for the autouse HTTP mock. Individual tests override the response.
_DEFAULT_URL = "https://example.com/"


@pytest.fixture(autouse=True)
def _suppress_noisy_loggers() -> Iterator[None]:
    """Keep httpx/MCP info logs off stderr during tests."""
    loggers = ("httpx", "httpcore", "mcp")
    previous = {name: logging.getLogger(name).level for name in loggers}
    for name in loggers:
        logging.getLogger(name).setLevel(logging.WARNING)
    yield
    for name, level in previous.items():
        logging.getLogger(name).setLevel(level)


@pytest.fixture(autouse=True)
def mock_fetch_http() -> Iterator[MagicMock]:
    """Mock fetch_url HTTP for every test — no real network requests."""
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response(
        text=f"<html><body><p>{DEFAULT_PAGE_TEXT}</p></body></html>",
        url=_DEFAULT_URL,
    )
    with patch("maestro.mcp_server.fetch_url.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client_cls.return_value.__exit__.return_value = False
        yield mock_client


@pytest.fixture
def in_process_mcp_factory() -> McpClientFactory:
    """Factory that connects the orchestrator to an in-process MCP server."""
    return lambda: in_process_mcp_session()


@pytest.fixture
def orchestrator(in_process_mcp_factory: McpClientFactory):
    from maestro.orchestrator import Orchestrator

    return Orchestrator(mcp_client_factory=in_process_mcp_factory)
