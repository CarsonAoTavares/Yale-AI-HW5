"""Builds the five-agent Campus Customs team and runs the Boss on a ticket."""

from __future__ import annotations

import uuid

from pydantic_ai.usage import RunUsage

from . import audit
from .accounting import build_accounting_agent
from .boss import build_boss_agent
from .config import MODEL_NAME, build_mcp_toolset, build_model
from .customer_service import build_customer_service_agent
from .delegation import AGENTS, TeamDeps, run_agent
from .facilities import build_facilities_agent
from .inventory import build_inventory_agent
from .mcp_client import HUMAN_ONLY_TOOLS
from .models import TicketDecision, TicketRunResult

_TOOLSET = None


def build_team() -> None:
    """Create all five agents on one model and one shared MCP connection."""
    global _TOOLSET
    model = build_model()
    # Agents never see human-only tools (e.g. executing a payment); only the
    # backend's approve route can call those.
    _TOOLSET = build_mcp_toolset().filtered(lambda ctx, tool: tool.name not in HUMAN_ONLY_TOOLS)
    AGENTS.update(
        boss=build_boss_agent(model, _TOOLSET),
        inventory=build_inventory_agent(model, _TOOLSET),
        accounting=build_accounting_agent(model, _TOOLSET),
        facilities=build_facilities_agent(model, _TOOLSET),
        customer_service=build_customer_service_agent(model, _TOOLSET),
    )


async def run_ticket(ticket_id: int, run_id: str | None = None) -> TicketRunResult:
    """Boss works one ticket, delegating as needed. Every step lands in the audit trail."""
    if not AGENTS:
        build_team()
    deps = TeamDeps(run_id=run_id or uuid.uuid4().hex[:12], ticket_id=ticket_id, role='boss', chain=('boss',))
    usage = RunUsage()
    audit.record('ticket_run_start', model=MODEL_NAME, **deps.audit_ctx())
    # Keep the MCP connection open for the whole run so nested agents share it.
    async with _TOOLSET:
        decision: TicketDecision = await run_agent(
            'boss',
            f'Work ticket {ticket_id} from the tickets table and return your final decision.',
            deps,
            usage=usage,
        )
    result = TicketRunResult(
        decision=decision,
        delegations=deps.delegations,
        model=MODEL_NAME,
        requests=usage.requests,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )
    audit.record(
        'ticket_run_finish',
        status=decision.status,
        delegations=len(deps.delegations),
        requests=usage.requests,
        total_tokens=usage.total_tokens,
        **deps.audit_ctx(),
    )
    return result
