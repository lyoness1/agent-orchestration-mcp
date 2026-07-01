"""MCP tool server exposing web research tools over stdio.

This module is decoupled from orchestration: it must not import agent or
orchestrator code so any MCP client can use it.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from maestro.mcp_server.fetch_url import fetch_url as _fetch_url

mcp = FastMCP("maestro-research-tools")


@mcp.tool()
def fetch_url(url: str) -> str:
    """Fetch a web page and return its main readable text.

    Use this to read the full content of a promising http(s) URL. Boilerplate
    (navigation, ads, scripts) is stripped and very long pages are truncated.
    On any failure a short message beginning with ``Error:`` is returned.
    """
    return _fetch_url(url)


def main() -> None:
    """Run the MCP server over stdio (launched as a subprocess by MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
