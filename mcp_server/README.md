# Campus Customs MCP Server

`server.py` is a FastMCP server, and the only way anything in this project reads or changes shop data. All five agents get their facts from these tools, and the FastAPI backend uses the same tools for the board, cash, and approved payments. There's no second data layer.

**Database:** `data/campus_customs_new.db`, the working copy. Override it with `CAMPUS_CUSTOMS_DB`. The server refuses to open the original `data/campus_customs.db`, which stays untouched so it can be restored.

**Run by hand:**

```bash
CAMPUS_CUSTOMS_DB=data/campus_customs_new.db .venv/bin/python mcp_server/server.py
```

The backend starts it automatically over stdio. `.mcp.json` at the project root registers it for a coding assistant as `campus-customs`.

## Tools

### First three (Problem 2)

| Tool | Tables | Use |
|---|---|---|
| `get_ticket(ticket_id)` | `tickets`, plus linked `invoices`, `leases`, `inventory` | One ticket and the records it points to |
| `check_stock(sku, size?, qty_needed?)` | `inventory` | On-hand by SKU and size; `can_fill` and `shortage` for an order |
| `get_lease(lease_id)` | `leases`, `desk`, `payments` | Rent amount, days until due from `desk.date_today`, rent already paid |

### Added for the agent team (Problem 5)

| Tool | Tables | Use |
|---|---|---|
| `list_tickets(status?)` | `tickets` | The whole board, open or resolved |
| `get_desk()` | `desk` | `date_today`, the shop's "today" |
| `get_pricing(sku, qty?, discount_pct?)` | `pricing` | Cost, list price, and margin at any discount; flags selling below cost |
| `list_vendors()` | `vendors`, `invoices`, `desk` | Lead days, arrival date if ordered today, blocked by an unpaid invoice? |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk`, `payments` | Amount, vendor, days overdue, payments recorded |
| `list_open_invoices()` | `invoices`, `vendors`, `desk` | Every unpaid invoice with days overdue |
| `get_cash_balance(account?)` | `cash_accounts` | Live balance (default `checking`) |
| `list_payments()` | `payments` | What has already been paid |
| `update_ticket_status(ticket_id, status, note)` | `tickets` (write) | Boss closes out a ticket with a note |
| `save_board_draft(ticket_id, audience, recipient, subject, body)` | `board_drafts` (write; created in the working copy) | Keeps a message draft on the board. Never sent. |

### Human-only (hidden from agents)

| Tool | Tables | Use |
|---|---|---|
| `execute_approved_payment(approval_id, kind, amount, ...)` | `cash_accounts`, `payments`, `invoices`, `leases`, `vendors`, `pricing` | Called only by the backend after a person clicks **Approve**. Checks the amount against the invoice, the rent, or `unit_cost × qty`. Refuses double payments, blocked vendors, and anything that would make the balance negative. Then subtracts the cash, records a `payments` row, and marks the invoice paid or moves the lease's `next_due` forward a month. All in one transaction. |
