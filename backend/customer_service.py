"""customer_service agent. Prompt: backend/prompts/customer_service.md"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from .delegation import TeamDeps, make_agent
from .models import AgentReport


def build_customer_service_agent(model: Any, toolset: Any) -> Agent[TeamDeps, AgentReport]:
    return make_agent('customer_service', AgentReport, model, toolset)
