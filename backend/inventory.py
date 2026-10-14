"""inventory agent. Prompt: backend/prompts/inventory.md"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from .delegation import TeamDeps, make_agent
from .models import AgentReport


def build_inventory_agent(model: Any, toolset: Any) -> Agent[TeamDeps, AgentReport]:
    return make_agent('inventory', AgentReport, model, toolset)
