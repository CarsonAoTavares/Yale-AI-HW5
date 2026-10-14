"""Append-only audit trail for every step of the agent loop.

Records go to output/audit_trail.json as one JSON array. Existing entries are
always kept; each call reads the array, appends, and writes it back atomically.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import messages as m

from .config import PROJECT_DIR

AUDIT_PATH = PROJECT_DIR / 'output' / 'audit_trail.json'
MAX_TEXT = 4000  # keep huge tool outputs from bloating the file

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f'... [truncated {len(value) - MAX_TEXT} chars]'
    return value


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return _clip(value)
    except TypeError:
        if hasattr(value, 'model_dump'):
            return _jsonable(value.model_dump(mode='json'))
        return _clip(str(value))


def _read_existing() -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding='utf-8') or '[]')
    except json.JSONDecodeError:
        # Never silently drop history: park the unreadable file and start fresh.
        AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f'.corrupt-{datetime.now():%Y%m%d%H%M%S}.json'))
        return []
    return data if isinstance(data, list) else [data]


def record(event: str, *, run_id: str, agent: str, depth: int, ticket_id: int | None, **details: Any) -> None:
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'run_id': run_id,
        'ticket_id': ticket_id,
        'agent': agent,
        'depth': depth,
        'event': event,
        **{k: _jsonable(v) for k, v in details.items()},
    }
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        entries = _read_existing()
        entries.append(entry)
        tmp = AUDIT_PATH.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(entries, indent=2), encoding='utf-8')
        os.replace(tmp, AUDIT_PATH)


def record_model_response(response: m.ModelResponse, **ctx: Any) -> None:
    """One model turn: what the model said and which tools it decided to call."""
    tool_calls = [
        {'tool': p.tool_name, 'tool_call_id': p.tool_call_id, 'args': _jsonable(p.args)}
        for p in response.parts
        if isinstance(p, m.ToolCallPart)
    ]
    text = '\n'.join(p.content for p in response.parts if isinstance(p, m.TextPart))
    record(
        'model_response',
        model=response.model_name,
        text=text or None,
        tool_calls=tool_calls,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        **ctx,
    )


def record_model_request(request: m.ModelRequest, **ctx: Any) -> None:
    """Tool results (and retry prompts) being sent back to the model."""
    for part in request.parts:
        if isinstance(part, m.ToolReturnPart):
            record('tool_result', tool=part.tool_name, tool_call_id=part.tool_call_id, output=_jsonable(part.content), **ctx)
        elif isinstance(part, m.RetryPromptPart):
            record('tool_retry', tool=part.tool_name, tool_call_id=part.tool_call_id, message=_jsonable(part.content), **ctx)
