"""Tests for the MCP fetch_url tool (HTTP mocked — no real network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from maestro.mcp_server.fetch_url import fetch_url
from maestro.mcp_server.server import mcp
from maestro.settings import settings


def _mock_response(
    *,
    status_code: int = 200,
    text: str = "",
    content_type: str = "text/html; charset=utf-8",
    url: str = "https://example.com/page",
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(
        status_code,
        text=text,
        headers={"content-type": content_type},
        request=request,
    )


def test_fetch_url_rejects_non_http_scheme() -> None:
    result = fetch_url("ftp://example.com/file")

    assert result.startswith("Error:")
    assert "not a valid http(s) URL" in result


def test_fetch_url_rejects_relative_url() -> None:
    result = fetch_url("/relative/path")

    assert result.startswith("Error:")
    assert "not a valid http(s) URL" in result


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_returns_text_from_html(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(
        text="<html><body><p>Hello world</p></body></html>",
    )

    result = fetch_url("https://example.com/page")

    assert result == "Hello world"
    mock_client.get.assert_called_once_with("https://example.com/page")


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_strips_scripts_and_styles(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(
        text=(
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert(1)</script><p>Visible</p></body></html>"
        ),
    )

    result = fetch_url("https://example.com/page")

    assert result == "Visible"
    assert "alert" not in result


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_handles_http_error(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    response = _mock_response(status_code=404, text="Not Found")
    mock_client.get.return_value = response

    result = fetch_url("https://example.com/missing")

    assert result == "Error: https://example.com/missing returned HTTP 404."


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_handles_timeout(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = httpx.TimeoutException("timed out")

    result = fetch_url("https://example.com/slow")

    expected = (
        f"Error: request to https://example.com/slow timed out after "
        f"{settings.MCP_REQUEST_TIMEOUT:g}s."
    )
    assert result == expected


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_handles_request_error(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.side_effect = httpx.RequestError("connection refused")

    result = fetch_url("https://example.com/down")

    assert result.startswith("Error: could not fetch https://example.com/down:")


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_rejects_non_text_content_type(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(
        text="binary",
        content_type="image/png",
    )

    result = fetch_url("https://example.com/image.png")

    assert result.startswith("Error:")
    assert "non-text" in result.lower()


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_accepts_plain_text_content_type(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(
        text="plain article",
        content_type="text/plain; charset=utf-8",
    )

    result = fetch_url("https://example.com/article.txt")

    assert result == "plain article"


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_returns_error_when_no_readable_content(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(text="<html><head></head></html>")

    result = fetch_url("https://example.com/empty")

    assert result == "Error: no readable content found at https://example.com/empty."


@patch("maestro.mcp_server.fetch_url.httpx.Client")
def test_fetch_url_truncates_long_content(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    long_text = "x" * (settings.MCP_MAX_CHARS + 100)
    mock_client.get.return_value = _mock_response(
        text=f"<html><body><p>{long_text}</p></body></html>",
        content_type="text/plain; charset=utf-8",
    )

    result = fetch_url("https://example.com/long")

    assert len(result) < len(long_text)
    assert f"[... truncated to {settings.MCP_MAX_CHARS} characters ...]" in result


def test_mcp_server_exposes_fetch_url_tool() -> None:
    tools = {tool.name: tool for tool in mcp._tool_manager._tools.values()}  # noqa: SLF001

    assert "fetch_url" in tools
    assert "Fetch a web page" in tools["fetch_url"].description
