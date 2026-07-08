"""Fetch a URL and return readable text for MCP clients."""

from __future__ import annotations

import re

import httpx

from maestro.settings import settings

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_TEXT_CONTENT_TYPES = (
    "text/",
    "application/json",
    "application/xml",
    "application/xhtml+xml",
    "application/javascript",
    "application/ld+json",
)


def _strip_html(html: str) -> str:
    """Crude HTML-to-text fallback for pages without obvious text nodes."""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _is_text_content_type(content_type: str) -> bool:
    lowered = content_type.lower().split(";", 1)[0].strip()
    return any(lowered.startswith(prefix) for prefix in _TEXT_CONTENT_TYPES)


def fetch_url(url: str) -> str:
    """Fetch a web page and return its main readable text.

    Failures are returned as strings beginning with ``Error:`` so callers can
    recover without the whole run crashing.
    """
    if not url.lower().startswith(("http://", "https://")):
        return f"Error: '{url}' is not a valid http(s) URL."

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=settings.MCP_REQUEST_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        return f"Error: request to {url} timed out after {settings.MCP_REQUEST_TIMEOUT:g}s."
    except httpx.HTTPStatusError as exc:
        return f"Error: {url} returned HTTP {exc.response.status_code}."
    except httpx.RequestError as exc:
        return f"Error: could not fetch {url}: {exc}."

    content_type = response.headers.get("content-type", "")
    if content_type and not _is_text_content_type(content_type):
        return f"Error: {url} returned non-text content ({content_type.split(';', 1)[0].strip()})."

    text = _strip_html(response.text).strip()
    if not text:
        return f"Error: no readable content found at {url}."

    if len(text) > settings.MCP_MAX_CHARS:
        text = (
            text[: settings.MCP_MAX_CHARS].rstrip()
            + f"\n\n[... truncated to {settings.MCP_MAX_CHARS} characters ...]"
        )
    return text
