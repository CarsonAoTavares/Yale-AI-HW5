"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentRole = Literal['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

AGENT_ROLES: tuple[AgentRole, ...] = ('boss', 'inventory', 'accounting', 'facilities', 'customer_service')


class Finding(BaseModel):
    """One fact an agent relies on, with where it came from so it can be checked."""

    fact: str = Field(description='The fact in plain words, including exact values (IDs, SKUs, sizes, amounts, dates).')
    source: str = Field(description='The MCP tool (and table) that returned this fact, or the agent that reported it.')


class ApprovalRequest(BaseModel):
    """A payment or purchase order prepared for a human to approve on the dashboard.

    Agents only prepare these. Nothing is paid until a person approves it.
    """

    kind: Literal['payment', 'purchase_order']
    ticket_id: int | None = None
    payee: str = Field(description='Vendor, landlord, or other party exactly as named in the database.')
    amount: float = Field(gt=0, description='Amount in dollars, taken from the database or computed from database values.')
    pay_from_account: str | None = Field(default=None, description='cash_accounts identifier the money would come from.')
    reference: str = Field(description='What this pays for, e.g. an invoice ID or lease ID from the database.')
    reason: str = Field(description='Why this payment or order is needed now.')
    cash_check: str = Field(description='Balance of the paying account versus the amount, as read from the database.')


class DraftMessage(BaseModel):
    """A message draft that stays on the board. Nobody emails customers or vendors."""

    audience: Literal['customer', 'vendor', 'landlord', 'internal']
    ticket_id: int | None = None
    recipient: str
    subject: str
    body: str


class AgentReport(BaseModel):
    """What a specialist agent hands back to whoever delegated to it."""

    agent: AgentRole
    ticket_id: int | None = None
    summary: str = Field(description='Two or three sentences answering the task that was delegated.')
    findings: list[Finding] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list, description='Database changes made through MCP tools, if any.')
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list, description='Anything that stops the work, e.g. an open invoice or low cash.')
    open_questions: list[str] = Field(default_factory=list)


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    status: Literal['resolved', 'awaiting_approval', 'blocked', 'needs_info']
    decision: str = Field(description='The final decision in one or two sentences.')
    reasoning: str = Field(description='Why, citing the specialists\' findings and the shop rules that applied.')
    agents_consulted: list[AgentRole] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class DelegationRecord(BaseModel):
    """One hand-off between agents, kept so the dashboard can show who talked to whom."""

    from_agent: AgentRole
    to_agent: AgentRole
    task: str
    depth: int
    result_summary: str | None = None
    error: str | None = None


class TicketRunResult(BaseModel):
    """Everything produced by one Boss run on one ticket."""

    decision: TicketDecision
    delegations: list[DelegationRecord]
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
