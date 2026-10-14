"""FastAPI backend for the Campus Customs operations dashboard.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# `uvicorn main:app` runs this file as a top-level module from backend/, so put
# the project root on the path and import the rest of the backend as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import approvals, audit  # noqa: E402
from backend.config import MODEL_NAME, ORIGINAL_DB, WORKING_DB  # noqa: E402
from backend.mcp_client import MCPToolError, call_tool  # noqa: E402
from backend.models import TicketRunResult  # noqa: E402
from backend.team import run_ticket  # noqa: E402

app = FastAPI(title='Campus Customs Operations API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)


class RunState(BaseModel):
    run_id: str
    ticket_id: int
    status: str  # running | finished | failed
    started_at: str
    finished_at: str | None = None
    result: TicketRunResult | None = None
    error: str | None = None


RUNS: dict[str, RunState] = {}
_tasks: set[asyncio.Task] = set()
_payment_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _running() -> list[RunState]:
    return [r for r in RUNS.values() if r.status == 'running']


async def _mcp(name: str, arguments: dict[str, Any] | None = None) -> Any:
    try:
        return await call_tool(name, arguments)
    except MCPToolError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # server missing, crashed, etc.
        raise HTTPException(status_code=503, detail=f'MCP server unavailable: {exc}') from exc


@app.get('/api/health')
async def health() -> dict[str, Any]:
    return {'ok': True, 'model': MODEL_NAME, 'working_db': WORKING_DB.name, 'working_db_exists': WORKING_DB.exists()}


# --- Tickets -----------------------------------------------------------------


@app.get('/api/tickets')
async def list_tickets() -> list[dict[str, Any]]:
    """All tickets with their open/resolved status, plus the latest agent run on each."""
    tickets = await _mcp('list_tickets')
    for t in tickets:
        runs = [r for r in RUNS.values() if r.ticket_id == t.get('ticket_id')]
        latest = max(runs, key=lambda r: r.started_at, default=None)
        if latest:
            t['latest_run'] = latest.model_dump(mode='json', exclude={'result'})
            t['latest_run']['decision_status'] = latest.result.decision.status if latest.result else None
        else:
            t['latest_run'] = None
    return tickets


async def _run_in_background(state: RunState) -> None:
    try:
        result = await run_ticket(state.ticket_id, run_id=state.run_id)
        if result.decision.approvals_needed:
            approvals.add_pending(state.run_id, state.ticket_id, result.decision.approvals_needed)
        state.result, state.status = result, 'finished'
    except Exception as exc:
        state.error, state.status = f'{type(exc).__name__}: {exc}', 'failed'
    state.finished_at = _now()


@app.post('/api/tickets/{ticket_id}/run', status_code=202)
async def run_ticket_route(ticket_id: int) -> RunState:
    """Start the agent team on one ticket. Poll /api/runs/{run_id} or /api/activity for progress."""
    if any(r.ticket_id == ticket_id for r in _running()):
        raise HTTPException(status_code=409, detail=f'Ticket {ticket_id} is already being worked.')
    state = RunState(run_id=uuid.uuid4().hex[:12], ticket_id=ticket_id, status='running', started_at=_now())
    RUNS[state.run_id] = state
    task = asyncio.create_task(_run_in_background(state))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return state


@app.get('/api/runs/{run_id}')
async def get_run(run_id: str) -> RunState:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail='Unknown run.')
    return RUNS[run_id]


# --- Activity ------------------------------------------------------------------


@app.get('/api/activity')
async def activity(
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Most recent audit-trail entries (messages, tool calls, tool results, delegations), newest first."""
    if not audit.AUDIT_PATH.exists():
        return []
    entries = json.loads(audit.AUDIT_PATH.read_text(encoding='utf-8') or '[]')
    if ticket_id is not None:
        entries = [e for e in entries if e.get('ticket_id') == ticket_id]
    if run_id is not None:
        entries = [e for e in entries if e.get('run_id') == run_id]
    return entries[-limit:][::-1]


# --- Approvals and payments ----------------------------------------------------


@app.get('/api/approvals')
async def list_approvals(status: approvals.ApprovalStatus | None = None) -> list[approvals.StoredApproval]:
    return approvals.list_approvals(status)


@app.post('/api/approvals/{approval_id}/approve')
async def approve(approval_id: str) -> approvals.StoredApproval:
    """A person clicked Approve: execute the payment or purchase order through MCP and update cash."""
    async with _payment_lock:  # one payment at a time, so double clicks can't pay twice
        item = approvals.get(approval_id)
        if item is None:
            raise HTTPException(status_code=404, detail='Unknown approval request.')
        if item.status != 'pending':
            raise HTTPException(status_code=409, detail=f'Request is already {item.status}.')
        req = item.request
        args = {
            'approval_id': item.id,
            'kind': req.kind,
            'payee': req.payee,
            'amount': req.amount,
            'pay_from_account': req.pay_from_account,
            'reference': req.reference,
        }
        audit.record('human_approved', run_id=item.run_id, agent='human', depth=0, ticket_id=item.ticket_id, request=req)
        try:
            result = await call_tool('execute_approved_payment', args)
        except MCPToolError as exc:  # e.g. insufficient cash: the tool refuses and nothing changes
            item = approvals.set_status(approval_id, 'failed', str(exc))
            audit.record('payment_rejected', run_id=item.run_id, agent='human', depth=0, ticket_id=item.ticket_id, error=str(exc))
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f'MCP server unavailable: {exc}') from exc
        item = approvals.set_status(approval_id, 'approved', result)
        audit.record('payment_executed', run_id=item.run_id, agent='human', depth=0, ticket_id=item.ticket_id, result=result)
        return item


@app.post('/api/approvals/{approval_id}/reject')
async def reject(approval_id: str) -> approvals.StoredApproval:
    item = approvals.get(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Unknown approval request.')
    if item.status != 'pending':
        raise HTTPException(status_code=409, detail=f'Request is already {item.status}.')
    item = approvals.set_status(approval_id, 'rejected')
    audit.record('human_rejected', run_id=item.run_id, agent='human', depth=0, ticket_id=item.ticket_id, request=item.request)
    return item


# --- Cash and reset ------------------------------------------------------------


@app.get('/api/cash')
async def cash() -> Any:
    """Current checking account balance from cash_accounts."""
    return await _mcp('get_cash_balance', {'account': 'checking'})


@app.post('/api/reset')
async def reset() -> dict[str, Any]:
    """Restore data/campus_customs_new.db from the untouched original for a fresh run."""
    if _running():
        raise HTTPException(status_code=409, detail='Wait for running tickets to finish before resetting.')
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail=f'Original database not found: {ORIGINAL_DB}')
    shutil.copy2(ORIGINAL_DB, WORKING_DB)
    voided = approvals.void_pending('Database was reset; this request no longer matches the data.')
    RUNS.clear()
    audit.record('database_reset', run_id='reset', agent='human', depth=0, ticket_id=None, voided_approvals=voided)
    return {'ok': True, 'restored': WORKING_DB.name, 'from': ORIGINAL_DB.name, 'voided_approvals': voided}
