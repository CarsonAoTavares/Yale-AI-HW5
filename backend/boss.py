"""boss agent. Prompt: backend/prompts/boss.md"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from .delegation import TeamDeps, make_agent
from .models import TicketDecision


def build_boss_agent(model: Any, toolset: Any) -> Agent[TeamDeps, TicketDecision]:
    return make_agent('boss', TicketDecision, model, toolset)
