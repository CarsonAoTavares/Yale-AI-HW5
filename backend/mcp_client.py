"""Direct MCP calls made by the backend routes (not by agents).

The routes read tickets and cash, and execute approved payments, through the
same MCP server the agents use, so there is still only one shop-data layer.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from .config import build_mcp_transport

# Tools only the backend may call, after a person clicks Approve. They are
# filtered out of the agents' toolset in backend/team.py.
HUMAN_ONLY_TOOLS = frozenset({'execute_approved_payment'})


class MCPToolError(RuntimeError):
    pass


# One client for every route call. Its stdio transport keeps the MCP server
# process alive between calls (fastmcp's keep_alive), so only the first call
# pays the several seconds it takes to start the server on a small host.
_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(build_mcp_transport())
    return _client


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with _get_client() as client:
        result = await client.call_tool(name, arguments or {}, raise_on_error=False)
    if result.is_error:
        message = ' '.join(getattr(c, 'text', '') for c in result.content).strip()
        raise MCPToolError(message or f'MCP tool {name} failed')
    if result.data is not None:
        return result.data
    if result.structured_content is not None:
        return result.structured_content
    return ' '.join(getattr(c, 'text', '') for c in result.content)
