"""The agent loop and the delegate tool that connects every agent to every other agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage

from . import audit
from .config import MAX_DELEGATION_DEPTH, TEAM_USAGE_LIMITS
from .models import AgentReport, AgentRole, DelegationRecord, TicketDecision

# Filled in by backend.team.build_team(); looked up at call time so any agent
# can reach any other agent without circular imports.
AGENTS: dict[AgentRole, Agent[TeamDeps, Any]] = {}


@dataclass
class TeamDeps:
    run_id: str
    ticket_id: int | None
    role: AgentRole
    depth: int = 0
    chain: tuple[AgentRole, ...] = ()
    delegations: list[DelegationRecord] = field(default_factory=list)  # shared by the whole run

    def audit_ctx(self) -> dict[str, Any]:
        return {'run_id': self.run_id, 'agent': self.role, 'depth': self.depth, 'ticket_id': self.ticket_id}


def team_context(ctx: RunContext[TeamDeps]) -> str:
    """Dynamic instructions: where this agent sits in the current run."""
    d = ctx.deps
    lines = [
        f'Current ticket: {d.ticket_id if d.ticket_id is not None else "none (ad-hoc task)"}.',
        f'Delegation chain so far: {" -> ".join(d.chain)} (depth {d.depth} of max {MAX_DELEGATION_DEPTH}).',
    ]
    if d.depth >= MAX_DELEGATION_DEPTH:
        lines.append('You are at the maximum depth: you cannot delegate further. Work with your own MCP tools and report.')
    return '\n'.join(lines)


async def run_agent(role: AgentRole, prompt: str, deps: TeamDeps, usage: RunUsage | None = None) -> Any:
    """Run one agent step by step, writing every model turn and tool result to the audit trail."""
    agent = AGENTS[role]
    ctx = deps.audit_ctx()
    audit.record('agent_start', prompt=prompt, chain=list(deps.chain), **ctx)
    try:
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=TEAM_USAGE_LIMITS) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    audit.record_model_response(node.model_response, **ctx)
                elif Agent.is_model_request_node(node):
                    audit.record_model_request(node.request, **ctx)
            output = run.result.output
            run_usage = run.usage
    except Exception as exc:
        audit.record('agent_error', error=f'{type(exc).__name__}: {exc}', **ctx)
        raise
    audit.record(
        'agent_finish',
        output=output,
        team_requests_so_far=run_usage.requests,
        team_tokens_so_far=run_usage.total_tokens,
        **ctx,
    )
    return output


async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentRole, task: str) -> AgentReport | TicketDecision | str:
    """Hand part of the work to another Campus Customs agent and get its report back.

    Args:
        to_agent: Who should do it: 'boss', 'inventory', 'accounting', 'facilities', or 'customer_service'.
        task: A complete, self-contained instruction. Include the ticket ID and every exact value
            (SKU, size, quantity, vendor, invoice ID, lease ID, amount, date) the other agent needs,
            and say what you want back. The other agent cannot see your conversation.
    """
    d = ctx.deps
    if to_agent == d.role:
        return 'Refused: you cannot delegate to yourself. Do this part with your own MCP tools.'
    if to_agent in d.chain:
        return (
            f'Refused: {to_agent} is already earlier in this chain ({" -> ".join(d.chain)}) and is waiting on you. '
            'Finish your part and put what you need from them in open_questions or blockers in your report.'
        )
    if d.depth >= MAX_DELEGATION_DEPTH:
        return 'Refused: delegation depth limit reached. Answer with what your own MCP tools show and list the gaps.'

    record = DelegationRecord(from_agent=d.role, to_agent=to_agent, task=task, depth=d.depth + 1)
    d.delegations.append(record)
    audit.record('delegation', to_agent=to_agent, task=task, **d.audit_ctx())

    child = TeamDeps(
        run_id=d.run_id,
        ticket_id=d.ticket_id,
        role=to_agent,
        depth=d.depth + 1,
        chain=(*d.chain, to_agent),
        delegations=d.delegations,
    )
    try:
        # Share ctx.usage so the team-wide token limits cover nested agents too.
        result = await run_agent(to_agent, task, child, usage=ctx.usage)
    except UsageLimitExceeded:
        raise  # out of budget: stop the whole ticket run, don't let agents keep retrying
    except Exception as exc:
        record.error = f'{type(exc).__name__}: {exc}'
        return f'{to_agent} could not finish: {record.error}'

    record.result_summary = getattr(result, 'summary', None) or getattr(result, 'decision', None)
    return result


def make_agent(role: AgentRole, output_type: type, model: Any, toolset: Any) -> Agent[TeamDeps, Any]:
    """Every agent gets: its own prompt file, the shared MCP toolset, and the delegate tool."""
    from .config import PROMPTS_DIR

    prompt = (PROMPTS_DIR / f'{role}.md').read_text(encoding='utf-8')
    return Agent(
        model,
        name=role,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=[prompt, team_context],
        toolsets=[toolset],
        tools=[delegate],
        retries=2,
    )
