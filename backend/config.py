"""Shared configuration: paths, the single allowed model, and the MCP connection."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
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

# The assignment allows exactly one model for every agent. It is deliberately
# not configurable so no other model can sneak in through an env var.
MODEL_NAME = 'gpt-6-luna'
PORTKEY_BASE_URL = 'https://ai.portkey.ai/v1'

# Token guardrails for one full ticket run (all agents and delegations combined).
TEAM_USAGE_LIMITS = UsageLimits(
    request_limit=int(os.getenv('TEAM_REQUEST_LIMIT', '60')),
    total_tokens_limit=int(os.getenv('TEAM_TOTAL_TOKENS_LIMIT', '400000')),
)

# How deep a delegation chain may go (boss -> accounting -> inventory = depth 2).
MAX_DELEGATION_DEPTH = int(os.getenv('MAX_DELEGATION_DEPTH', '3'))


def build_model() -> OpenAIChatModel:
    api_key = os.getenv('PORTKEY_API_KEY')
    if not api_key:
        raise RuntimeError('PORTKEY_API_KEY is not set. Add it to Homework 5/.env.')
    provider = OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL)
    return OpenAIChatModel(MODEL_NAME, provider=provider)


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
