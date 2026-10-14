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


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with Client(build_mcp_transport()) as client:
        result = await client.call_tool(name, arguments or {}, raise_on_error=False)
    if result.is_error:
        message = ' '.join(getattr(c, 'text', '') for c in result.content).strip()
        raise MCPToolError(message or f'MCP tool {name} failed')
    if result.data is not None:
        return result.data
    if result.structured_content is not None:
        return result.structured_content
    return ' '.join(getattr(c, 'text', '') for c in result.content)
