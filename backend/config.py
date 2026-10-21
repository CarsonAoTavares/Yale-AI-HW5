"""Shared configuration: paths, the single allowed model, and the MCP connection."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.usage import UsageLimits

PROJECT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_DIR / 'backend'
PROMPTS_DIR = BACKEND_DIR / 'prompts'
DATA_DIR = PROJECT_DIR / 'data'
ORIGINAL_DB = DATA_DIR / 'campus_customs.db'
WORKING_DB = DATA_DIR / 'campus_customs_new.db'
MCP_SERVER_SCRIPT = PROJECT_DIR / 'mcp_server' / 'server.py'

# Project .env first, then the shared AI Foundation/.env as a fallback.
load_dotenv(PROJECT_DIR / '.env')
load_dotenv(PROJECT_DIR.parent / '.env')
os.environ.setdefault('PYDANTIC_AI_NO_BANNER', '1')

# Every agent runs on one model. The graded submission (main branch) used
# gpt-6-luna through Portkey; this hosted copy uses Claude with an Anthropic key.
# Low effort keeps runs cheap; thinking stays on (Opus 5.5 can't turn it off).
MODEL_NAME = 'claude-opus-5-5'
MODEL_EFFORT = 'low'

# Token guardrails for one full ticket run (all agents and delegations combined).
TEAM_USAGE_LIMITS = UsageLimits(
    request_limit=int(os.getenv('TEAM_REQUEST_LIMIT', '60')),
    total_tokens_limit=int(os.getenv('TEAM_TOTAL_TOKENS_LIMIT', '400000')),
)

# How deep a delegation chain may go (boss -> accounting -> inventory = depth 2).
MAX_DELEGATION_DEPTH = int(os.getenv('MAX_DELEGATION_DEPTH', '3'))


def build_model() -> AnthropicModel:
    if not os.getenv('ANTHROPIC_API_KEY'):
        raise RuntimeError('ANTHROPIC_API_KEY is not set. Add it to Homework 5/.env.')
    # Retry transient errors (429/5xx) per request, with backoff, so one blip
    # doesn't throw away a whole multi-agent run.
    client = AsyncAnthropic(max_retries=6, timeout=300)
    settings = AnthropicModelSettings(
        anthropic_effort=MODEL_EFFORT,
        # If a safety classifier declines a request, the API retries it on a
        # fallback model inside the same call instead of stopping the run.
        anthropic_betas=['server-side-fallback-2026-07-01'],
        extra_body={'fallbacks': 'default'},
    )
    return AnthropicModel(MODEL_NAME, provider=AnthropicProvider(anthropic_client=client), settings=settings)


def build_mcp_transport() -> StdioTransport:
    return StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        env={**os.environ, 'CAMPUS_CUSTOMS_DB': str(WORKING_DB)},
        cwd=str(PROJECT_DIR),
    )


def build_mcp_toolset() -> MCPToolset:
    """Every shop fact the agents see comes through this MCP connection."""
    return MCPToolset(build_mcp_transport(), id='campus_customs')
