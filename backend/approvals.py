"""Payment and purchase-order requests waiting for a person on the dashboard.

Agents only *prepare* ApprovalRequests. They are stored here as `pending`, and
nothing is paid until the approve route runs for that request.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel

from .config import PROJECT_DIR
from .models import ApprovalRequest

APPROVALS_PATH = PROJECT_DIR / 'output' / 'approvals.json'

ApprovalStatus = Literal['pending', 'approved', 'rejected', 'failed', 'void']

_lock = threading.Lock()


class StoredApproval(BaseModel):
    id: str
    run_id: str
    ticket_id: int | None
    created_at: str
    status: ApprovalStatus = 'pending'
    request: ApprovalRequest
    decided_at: str | None = None
    result: Any = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[StoredApproval]:
    if not APPROVALS_PATH.exists():
        return []
    return [StoredApproval.model_validate(a) for a in json.loads(APPROVALS_PATH.read_text(encoding='utf-8') or '[]')]


def _save(items: list[StoredApproval]) -> None:
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPROVALS_PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps([a.model_dump(mode='json') for a in items], indent=2), encoding='utf-8')
    os.replace(tmp, APPROVALS_PATH)


def add_pending(run_id: str, ticket_id: int | None, requests: list[ApprovalRequest]) -> list[StoredApproval]:
    new = [
        StoredApproval(id=uuid.uuid4().hex[:10], run_id=run_id, ticket_id=ticket_id, created_at=_now(), request=r)
        for r in requests
    ]
    with _lock:
        _save(_load() + new)
    return new


def list_approvals(status: ApprovalStatus | None = None) -> list[StoredApproval]:
    with _lock:
        items = _load()
    return [a for a in items if status is None or a.status == status]


def get(approval_id: str) -> StoredApproval | None:
    return next((a for a in list_approvals() if a.id == approval_id), None)


def set_status(approval_id: str, status: ApprovalStatus, result: Any = None) -> StoredApproval:
    with _lock:
        items = _load()
        for a in items:
            if a.id == approval_id:
                a.status, a.result, a.decided_at = status, result, _now()
                _save(items)
                return a
    raise KeyError(approval_id)


def void_pending(reason: str) -> int:
    """After a database reset, old requests no longer match the data."""
    with _lock:
        items = _load()
        count = 0
        for a in items:
            if a.status == 'pending':
                a.status, a.result, a.decided_at = 'void', reason, _now()
                count += 1
        _save(items)
    return count
