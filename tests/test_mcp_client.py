"""Integration tests for the MCP client (real subprocess, mocked HTTP)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import anyio

from maestro.mcp_client import MaestroMcpClient, default_server_params
from maestro.mcp_server.fetch_url import MAX_CHARS
from mcp_test_helpers import in_process_client, mock_response, server_params


def test_default_server_params_falls_back_to_python_module() -> None:
    params = default_server_params()

    assert params.command == sys.executable or params.command.endswith("maestro-mcp")
    if params.command == sys.executable:
        assert params.args == ["-m", "maestro.mcp_server"]


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_client_fetch_url_returns_page_text(mock_client_cls: MagicMock) -> None:
    page_text = "Hello from MCP"
    url = "https://example.com/page"
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response(
        text=f"<html><body><p>{page_text}</p></body></html>",
        url=url,
    )

    async def run() -> str:
        async with in_process_client() as client:
            return await client.fetch_url(url)

    result = anyio.run(run)

    assert result == page_text
    mock_client.get.assert_called_once_with(url)


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_client_fetch_url_surfaces_server_error_strings(mock_client_cls: MagicMock) -> None:
    url = "https://example.com/missing"
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response(status_code=404, text="Not Found", url=url)

    async def run() -> str:
        async with in_process_client() as client:
            return await client.fetch_url(url)

    result = anyio.run(run)

    assert result == f"Error: {url} returned HTTP 404."


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_client_fetch_url_truncates_long_pages(mock_client_cls: MagicMock) -> None:
    url = "https://example.com/long"
    long_text = "z" * (MAX_CHARS + 50)
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response(
        text=f"<html><body><p>{long_text}</p></body></html>",
        content_type="text/plain; charset=utf-8",
        url=url,
    )

    async def run() -> str:
        async with in_process_client() as client:
            return await client.fetch_url(url)

    result = anyio.run(run)

    assert f"[... truncated to {MAX_CHARS} characters ...]" in result


def test_subprocess_client_rejects_invalid_url_without_network() -> None:
    async def run() -> str:
        async with MaestroMcpClient(server_params()) as client:
            return await client.fetch_url("ftp://example.com/file")

    result = anyio.run(run)

    assert result.startswith("Error:")
    assert "not a valid http(s) URL" in result


def test_subprocess_client_connect_and_close() -> None:
    async def run() -> None:
        client = MaestroMcpClient(server_params())
        await client.connect()
        await client.close()
        await client.close()

    anyio.run(run)
