# Campus Customs Agent Harness

This file describes how the Campus Customs agent team is wired: the database, the MCP tools, the agents, and the safety limits. It grows with each problem.

> **Pending:** the Homework 5 database (`data/campus_customs.db`) isn't in the project yet. The **Database tables** and **MCP tools** sections below get filled in from the real tables once it's added. Nothing in them will be guessed.

---

## Database tables

_Pending database._ For each table (`desk`, `tickets`, `inventory`, `pricing`, `vendors`, `leases`, `cash_accounts`, `payments`, `invoices`): its fields, and one line on why it matters to the agents.

---

## MCP tools

_Pending database._ Server: `mcp_server/server.py` (FastMCP), reading and writing `data/campus_customs_new.db`. For each tool: the tables it uses, the ticket it unlocks (101, 102, 103), and why it's the right tool for that ticket.

Every shop fact the agents use comes through these MCP tools. The backend has no second data layer that bypasses MCP.

---

## Agents

All five agents run on **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`). The model name is hard-coded in `backend/config.py` with no override, so no other model can be used. Each agent has its own prompt file, the shared MCP toolset, and the `delegate` tool.

| Agent | Code | Prompt | Output | Owns |
|---|---|---|---|---|
| Boss | `backend/boss.py` | `backend/prompts/boss.md` | `TicketDecision` | Reads the ticket, decides who to involve, makes the final call and sets the status (`resolved`, `awaiting_approval`, `blocked`, `needs_info`) |
| Inventory | `backend/inventory.py` | `backend/prompts/inventory.md` | `AgentReport` | Stock by SKU and size, shortages, which vendors can restock, lead times, vendor blocks |
| Accounting | `backend/accounting.py` | `backend/prompts/accounting.md` | `AgentReport` | Cash balances, invoices, margins, preparing payment and purchase-order approval requests |
| Facilities | `backend/facilities.py` | `backend/prompts/facilities.md` | `AgentReport` | Leases, rent due and overdue, landlord drafts |
| Customer Service | `backend/customer_service.py` | `backend/prompts/customer_service.md` | `AgentReport` | Customer message drafts kept on the board |

Data types live in `backend/models.py`. The team is assembled in `backend/team.py`.

### How agents talk to each other

- **Full connectivity.** Every agent has the same `delegate(to_agent, task)` tool (`backend/delegation.py`) and can name any of the other four as `to_agent`. The called agent runs with its own prompt and tools and returns its report (or the Boss's decision) as the tool result.
- **No cycles.** An agent can't delegate to itself, or to an agent that is already earlier in the current chain and waiting on it (for example, inventory can't call back to the Boss that called it). It puts what it needs in `open_questions` or `blockers` instead, and the caller handles it.
- **Depth limit.** A chain can be at most `MAX_DELEGATION_DEPTH` (default 3) hand-offs deep, for example boss → inventory → accounting.
- **Self-contained tasks.** The called agent can't see the caller's conversation, so prompts require every task to carry the ticket ID and exact values.

### Audit trail

Every step of the agent loop is appended to `output/audit_trail.json` (`backend/audit.py`). Existing entries are never cleared. Each record has a timestamp, `run_id`, `ticket_id`, agent, delegation depth, and event:

| Event | What it records |
|---|---|
| `ticket_run_start` / `ticket_run_finish` | Model used; final status, number of delegations, requests and tokens for the run |
| `agent_start` | The prompt or task the agent was given and the delegation chain |
| `model_response` | Model name, any text, every tool call with its arguments, tokens for that turn |
| `tool_result` / `tool_retry` | What each MCP or delegate tool returned (long outputs clipped at 4,000 characters) |
| `delegation` | Who handed what task to whom |
| `agent_finish` / `agent_error` | The agent's structured output, or the error, plus running team token totals |

---

## Backend routes

FastAPI app in `backend/main.py`, started from `backend/` with `uvicorn main:app --reload --port 8000`, at `http://localhost:8000`. Shop data (tickets, cash, payments) goes through the MCP server, the same as for the agents.

- `GET /api/health`: confirms the backend is up and shows the model (`gpt-6-luna`) and whether the working database exists.
- `GET /api/tickets`: all tickets with their open or resolved status (MCP `list_tickets`), plus each ticket's latest agent run.
- `POST /api/tickets/{ticket_id}/run`: starts the agent team (Boss first) on one ticket in the background and returns a `run_id`.
- `GET /api/runs/{run_id}`: status of one run (running, finished, failed) and, when done, the Boss's decision, delegations, and token usage.
- `GET /api/activity?limit=&ticket_id=&run_id=`: newest audit-trail entries (agent messages, tool calls, tool results, delegations) so the board can refresh.
- `GET /api/approvals?status=`: payment and purchase-order requests the agents prepared, filterable by `pending`, `approved`, `rejected`, `failed`, or `void`.
- `POST /api/approvals/{approval_id}/approve`: a person clicked Approve. Executes the payment or purchase through MCP `execute_approved_payment`, which updates cash and the matching record, and refuses if cash is short.
- `POST /api/approvals/{approval_id}/reject`: a person clicked Reject. Marks the request rejected; nothing is paid.
- `GET /api/cash`: current checking balance from `cash_accounts` (MCP `get_cash_balance`).
- `POST /api/reset`: copies the original `campus_customs.db` over `campus_customs_new.db` for a fresh run, and voids pending approvals, which no longer match the data.

`execute_approved_payment` is hidden from every agent's toolset, so only the approve route (a person's click) can make a payment.

---

## Safety

**Real customers**
- Agents never send anything. Customer, vendor, and landlord messages are `DraftMessage` objects saved on the board for a person to review.
- Customer drafts must not promise discounts, refunds, or dates the data and the Boss haven't confirmed, and must not expose internal details (vendor problems, cash, margins).

**Money**
- Every payment and purchase order is an `ApprovalRequest` that a person approves on the dashboard. Agents prepare requests, and prompts forbid completing a payment without a human approval.
- Each request must state the paying account's balance against the amount. The payment tool (added with the MCP tools) must reject any payment that would make a balance negative.
- Accounting checks `payments` so an invoice or rent period is never paid twice. Only cash outflows count; expected revenue is never treated as available cash.
- Vendors with an open unpaid invoice are flagged as blocked, because they won't ship.

**Data**
- Every prompt says never invent data. Values must come from MCP tool results, and reports list a source for each finding.
- Agents only change `data/campus_customs_new.db`. The original `data/campus_customs.db` is never written to, and the backend will restore the working copy from it before each full run through the tickets.

**Token limits**
- One ticket run, including every nested delegation, shares one usage counter capped at **60 model requests** and **400,000 total tokens** (`TEAM_REQUEST_LIMIT`, `TEAM_TOTAL_TOKENS_LIMIT`). Hitting a cap stops the whole run instead of letting agents retry.
- Delegation depth is capped at 3 and cycles are refused, so agents can't ping-pong.
- Each agent gets 2 retries for malformed tool calls or output.
- Prompts tell agents to delegate each piece of work once with a precise task, and not to delegate what one MCP call can answer.
- Token counts per model turn and per run are written to the audit trail for monitoring.
