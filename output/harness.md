# Campus Customs Agent Harness

This file describes how the Campus Customs agent team is wired: the database, the MCP tools, the agents, the backend routes, the dashboard, and the safety rules.

---

## Database tables

`data/campus_customs.db` is the original and is never written. `data/campus_customs_new.db` is the working copy the MCP server reads and writes. The starting data is small: 1 desk row, 3 tickets, 10 inventory rows, 4 prices, 3 vendors, 1 invoice, 1 lease, 1 cash account, 0 payments.

| Table | Fields | Why it matters to the agents |
|---|---|---|
| `desk` | `date_today`, `notes` | `date_today` (2026-08-31) is "today" for every overdue and lead-time calculation, never the real date. |
| `tickets` | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The board. Each ticket's links (`sku`/`size`/`qty`, `lease_id`, `invoice_id`) tell the Boss which specialist and which records it needs. |
| `inventory` | `sku`, `name`, `size`, `qty`, `location` (key: `sku` + `size`) | What Inventory checks for orders; stock is per size, so a tee in M doesn't fill an order for S. |
| `pricing` | `sku`, `unit_cost`, `list_price` | Accounting's margin math for discounts and the cost of any purchase order. |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Who can restock what, and the only allowed source of lead times. |
| `invoices` | `id`, `vendor_id`, `amount`, `due_date`, `status`, `description` | Money the shop owes. An open one blocks that vendor from shipping anything new. |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Facilities' rent facts: how much, to whom, and when. |
| `cash_accounts` | `name`, `balance`, `date` | The `checking` balance every payment comes out of. It can never go negative. |
| `payments` | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The record of approved payments, used to avoid paying anything twice. Empty at the start. |

### How the three open tickets link to the other tables

- **101 `customer_order`**: Tauhid Zaman wants 1 `CC-TEE-WHITE` (Classic Bulldog Tee) in **S**. `inventory` has **0** in S. The ticket links `invoice_id` **501**: Bulldog Print Co (`vendor_id` 1, apparel reprint, 5 lead days) is owed **$840.00** for "Rush reprint CC-TEE-WHITE S", due 2026-08-28, still **open**, so 3 days overdue. The reprint that would fill this order is stuck behind that unpaid invoice.
- **102 `rent_notice`**: Elm City Properties says rent is due in 2 days. It links `lease_id` **1**: Chapel Street shop, **$2,400.00** a month, `next_due` **2026-09-02**, which is 2 days after `date_today`.
- **103 `price_override`**: Yale AI Club wants **20** `CC-HOOD-NAVY` (Basic Hoodie Big Yale) in **M** at a bulk discount. `inventory` has **8** in M (short 12; L has 14, S 4, XL 6). `pricing`: cost **$22.00**, list **$58.00**. No invoice or lease is linked.
- **Cash**: `checking` starts at **$3,400.00**. Paying invoice 501 ($840) and rent ($2,400) leaves $160, which can't cover a $264 reprint of 12 hoodies (12 × $22).

---

## MCP tools

Server: `mcp_server/server.py` (FastMCP) over `data/campus_customs_new.db`. Every shop fact the agents use comes through these tools. The backend has no second data layer that bypasses MCP. The routes for tickets, cash, and approved payments call the same server. `mcp_server/README.md` has the short list.

### The first three tools (Problem 2)

| Tool | Reads | Unlocks | Why it's the right tool for that ticket |
|---|---|---|---|
| `get_ticket(ticket_id)` | `tickets`, plus the linked `invoices`, `leases`, `inventory` rows | **101**, **102**, **103** | Every ticket points at other records (101 at invoice 501 and tee S stock, 102 at lease 1, 103 at hoodie M stock), and this pulls the ticket and those records in one call, so the Boss can see what kind of work it is before delegating. |
| `check_stock(sku, size, qty_needed)` | `inventory` | **101**, **103** | 101 needs 1 `CC-TEE-WHITE` in S and 103 needs 20 `CC-HOOD-NAVY` in M. This returns `on_hand`, `can_fill`, and the exact `shortage` (1 and 12), the number both tickets turn on. |
| `get_lease(lease_id)` | `leases`, `desk`, `payments` | **102** | The rent notice only says "due in 2 days." This confirms $2,400 to Elm City Properties, `next_due` 2026-09-02 measured from `desk.date_today` (2 days), and that no rent payment is already recorded, so it isn't paid twice. |

### Tools added for the agent team (Problem 5)

| Tool | Tables | Unlocks | What it's for |
|---|---|---|---|
| `list_tickets(status?)` | `tickets` | board | The dashboard's ticket list, with each ticket's open or resolved status. |
| `get_desk()` | `desk` | 101, 102 | `date_today`, so "overdue" (invoice 501) and "due in 2 days" (lease 1) use the shop's date. |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk`, `payments` | **101** | Invoice 501: $840 to Bulldog Print Co, `days_overdue` 3, no payment recorded. This is the blocker on the tee. |
| `list_open_invoices()` | `invoices`, `vendors`, `desk` | 101 | Accounting's sweep for anything unpaid. |
| `list_vendors()` | `vendors`, `invoices`, `desk` | **101**, **103** | Lead days, arrival date if ordered today, and `blocked_by_unpaid_invoice` (Bulldog Print Co is blocked until 501 is paid). |
| `get_pricing(sku, qty, discount_pct)` | `pricing` | **103** | Margin on 20 hoodies at any discount (for example 10% off: $52.20 each, $30.20 margin), so the discount is checked against cost without hand arithmetic. |
| `get_cash_balance(account)` | `cash_accounts` | 101, 102, 103, board | The live checking balance. Accounting reads it before every request; the Cash panel shows it. |
| `list_payments()` | `payments` | 101, 102 | Prevents double payment. |
| `update_ticket_status(ticket_id, status, note)` | `tickets` (write) | 101, 102, 103 | The Boss marks the outcome on the board; the backend marks a ticket resolved after its payments are approved. |
| `save_board_draft(...)` | `board_drafts` (write; created in the working copy) | 101, 103 | Customer replies (Tauhid Zaman, Yale AI Club) stay on the board as drafts. Nothing is emailed. |

### Human-only tool

| Tool | Tables | What it does |
|---|---|---|
| `execute_approved_payment(...)` | `cash_accounts`, `payments`, `invoices`, `leases`, `vendors`, `pricing` | Filtered out of every agent's toolset in `backend/team.py`; only `POST /api/approvals/{id}/approve` calls it. Checks the amount against invoice 501, lease 1's rent, or `unit_cost × qty`, and refuses double payments, blocked vendors, and overdrafts. Then, in one transaction, subtracts the cash, inserts a `payments` row (`approved_by` = dashboard user plus the approval id), and marks the invoice `paid` or moves `next_due` forward a month. |

### Connecting a coding assistant

`.mcp.json` registers the server as `campus-customs` (stdio, `CAMPUS_CUSTOMS_DB=data/campus_customs_new.db`). `output/mcp_smoke.json` shows the three Problem 2 tools called through that config, each output checked against the same rows queried directly from the database.

---

## Agents

All five agents run on **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`, `https://api.portkey.ai/v1`). The model name is hard-coded in `backend/config.py` with no override, so no other model can be used. It's called through PydanticAI's `OpenAIResponsesModel`, because Portkey rejects function tools for `gpt-6-luna` on chat completions. The OpenAI client retries temporary gateway errors (429/5xx) up to 6 times per request. Responses report the model as `gpt-6-luna-global`, which is Portkey's Azure deployment name for the same `gpt-6-luna`. No other model is ever requested. Each agent has its own prompt file, the shared MCP toolset, and the `delegate` tool.

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

## Dashboard

React + Vite + TypeScript in `frontend/`, served at `http://localhost:5173` (`npm run dev`). It calls the backend at `http://localhost:8000` directly (`frontend/src/api.ts`), which allows that origin through CORS. The full design rationale is in `output/design.md`.

- **The Board (left):** every ticket from `GET /api/tickets` as a ticket stub with its status chip; a green RESOLVED stamp lands when the ticket is resolved.
- **Case file (center):** the selected ticket's database fields and **Dispatch the team** (`POST /api/tickets/{id}/run`).
- **Agent floor and live feed:** the five agents in fixed colors. While a run is going the board polls `GET /api/runs/{run_id}` and `GET /api/activity` every 1.2 seconds and shows each message, MCP tool call, tool result, and delegation, indented by depth.
- **Who did what:** after the run, the Boss's decision and one card per agent from the run's delegations, plus drafts left on the board.
- **Cash and approvals (right):** the checking balance from `GET /api/cash`, which shows the drop after each payment, and pending requests from `GET /api/approvals` drawn as checks with **Approve** and **Reject**.
- **↺ Fresh run:** `POST /api/reset`.

---

## Safety

**Real customers**
- Agents never send anything. Customer, vendor, and landlord messages are `DraftMessage` objects saved on the board for a person to review.
- Customer drafts must not promise discounts, refunds, or dates the data and the Boss haven't confirmed, and must not expose internal details (vendor problems, cash, margins).

**Money**
- Every payment and purchase order is an `ApprovalRequest` that a person approves on the dashboard. Agents prepare requests, and prompts forbid completing a payment without a human approval.
- Each request must state the paying account's balance against the amount. `execute_approved_payment` re-checks the amount against the database and rejects any payment that would make a balance negative (for example, $264 of hoodies against $160 left after invoice 501 and rent).
- Accounting checks `payments` so an invoice or rent period is never paid twice. Only cash outflows count; expected revenue is never treated as available cash.
- Vendors with an open unpaid invoice are flagged as blocked, because they won't ship.

**Data**
- Every prompt says never invent data. Values must come from MCP tool results, and reports list a source for each finding.
- Agents only change `data/campus_customs_new.db`. The original `data/campus_customs.db` is never written to, and `POST /api/reset` (the dashboard's **↺ Fresh run**) restores the working copy from it before each full run through the tickets.

**Token limits**
- One ticket run, including every nested delegation, shares one usage counter capped at **60 model requests** and **400,000 total tokens** (`TEAM_REQUEST_LIMIT`, `TEAM_TOTAL_TOKENS_LIMIT`). Hitting a cap stops the whole run instead of letting agents retry.
- Delegation depth is capped at 3 and cycles are refused, so agents can't ping-pong.
- Each agent gets 2 retries for malformed tool calls or output.
- Prompts tell agents to delegate each piece of work once with a precise task, and not to delegate what one MCP call can answer.
- Token counts per model turn and per run are written to the audit trail for monitoring.

---

## Final run (evidence)

After `POST /api/reset`, tickets 101, 102, and 103 were run from the dashboard, and both payments were approved on the board. Results are in `output/resolved_tickets.json`, screenshots in `output/resolved_board.html`, and the Expected vs Actual plan and cash breakdown in `output/desk_tickets.html`.

| Ticket | Agents | Approval | Checking | Status |
|---|---|---|---|---|
| 101 | Boss, Inventory, Accounting, Customer Service | invoice 501, $840.00 | $3,400.00 → $2,560.00 | resolved |
| 102 | Boss, Facilities, Accounting | rent lease 1, $2,400.00 | $2,560.00 → $160.00 | resolved |
| 103 | Boss, Inventory, Accounting, Customer Service | none (no purchase order: $264 > $160) | $160.00 → $160.00 | resolved |

The ending balance, $160.00, matches `cash_accounts.checking`. `output/audit_trail.json` also keeps the earlier attempts: one blocked by the chat-completions tool error, one cut off by a Portkey 500, and one where the Boss stopped at `needs_info` on 103 before its prompt was tightened. The audit trail is append-only, so those attempts stay in it.
