"""accounting agent. Prompt: backend/prompts/accounting.md"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from .delegation import TeamDeps, make_agent
from .models import AgentReport


def build_accounting_agent(model: Any, toolset: Any) -> Agent[TeamDeps, AgentReport]:
    return make_agent('accounting', AgentReport, model, toolset)
