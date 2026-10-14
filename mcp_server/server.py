"""Campus Customs MCP server (FastMCP).

Every shop fact the agents and the backend use comes from these tools, over
the working database data/campus_customs_new.db. The original
data/campus_customs.db is never opened here.

Run by hand:  CAMPUS_CUSTOMS_DB=data/campus_customs_new.db python mcp_server/server.py
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv('CAMPUS_CUSTOMS_DB', PROJECT_DIR / 'data' / 'campus_customs_new.db'))
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_DIR / DB_PATH
if DB_PATH.name == 'campus_customs.db':
    raise SystemExit('Refusing to open the original database. Point CAMPUS_CUSTOMS_DB at campus_customs_new.db.')

TicketStatus = Literal['open', 'in_progress', 'awaiting_approval', 'resolved', 'blocked', 'needs_info']

mcp = FastMCP(
    'campus-customs',
    instructions=(
        'Tools for the Campus Customs shop database. Use desk.date_today as today. '
        'Never invent values: every fact must come from a tool result.'
    ),
)


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    if not DB_PATH.exists():
        raise ToolError(f'Working database not found at {DB_PATH}. Copy campus_customs.db to campus_customs_new.db first.')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def today(conn: sqlite3.Connection) -> date:
    return date.fromisoformat(conn.execute('SELECT date_today FROM desk').fetchone()[0])


def open_invoices_for(conn: sqlite3.Connection, vendor_id: int) -> list[dict[str, Any]]:
    return rows(conn, "SELECT * FROM invoices WHERE vendor_id = ? AND status != 'paid'", (vendor_id,))


# ---------------------------------------------------------------------------
# Problem 2: the first three tools
# ---------------------------------------------------------------------------


@mcp.tool
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Read one ticket from the board (tickets table) with the records it links to.

    Returns the ticket row plus, when the ticket references them, the linked
    invoice (invoice_id), lease (lease_id), and the inventory rows for its SKU/size.
    """
    with db() as conn:
        ticket = one(conn, 'SELECT * FROM tickets WHERE id = ?', (ticket_id,))
        if ticket is None:
            raise ToolError(f'No ticket with id {ticket_id}.')
        linked: dict[str, Any] = {}
        if ticket['invoice_id'] is not None:
            linked['invoice'] = one(conn, 'SELECT * FROM invoices WHERE id = ?', (ticket['invoice_id'],))
        if ticket['lease_id'] is not None:
            linked['lease'] = one(conn, 'SELECT * FROM leases WHERE id = ?', (ticket['lease_id'],))
        if ticket['sku']:
            linked['inventory'] = rows(
                conn, 'SELECT * FROM inventory WHERE sku = ? AND (? IS NULL OR size = ?)', (ticket['sku'], ticket['size'], ticket['size'])
            )
        return {'ticket': ticket, 'linked': linked}


@mcp.tool
def check_stock(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict[str, Any]:
    """Units on hand for a SKU (inventory table), optionally for one size.

    If qty_needed is given, also reports whether that size can be filled and the
    exact shortage.
    """
    with db() as conn:
        found = rows(
            conn, 'SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND (? IS NULL OR size = ?) ORDER BY size',
            (sku, size, size),
        )
    if not found:
        raise ToolError(f'No inventory rows for sku={sku!r}' + (f' size={size!r}.' if size else '.'))
    result: dict[str, Any] = {'sku': sku, 'rows': found}
    if size and qty_needed is not None:
        on_hand = found[0]['qty']
        result.update(on_hand=on_hand, qty_needed=qty_needed, can_fill=on_hand >= qty_needed, shortage=max(qty_needed - on_hand, 0))
    return result


@mcp.tool
def get_lease(lease_id: int) -> dict[str, Any]:
    """Read a lease (leases table) and how many days until rent is due, counted from desk.date_today.

    Also lists rent payments already recorded for this lease, so rent is never paid twice.
    """
    with db() as conn:
        lease = one(conn, 'SELECT * FROM leases WHERE id = ?', (lease_id,))
        if lease is None:
            raise ToolError(f'No lease with id {lease_id}.')
        t = today(conn)
        due = date.fromisoformat(lease['next_due'])
        paid = rows(conn, "SELECT * FROM payments WHERE kind = 'rent' AND ref_id = ?", (lease_id,))
    return {
        'lease': lease,
        'date_today': t.isoformat(),
        'days_until_due': (due - t).days,
        'overdue': due < t,
        'rent_payments_recorded': paid,
    }


# ---------------------------------------------------------------------------
# Problem 5: tools added so the team can work all three tickets
# ---------------------------------------------------------------------------


@mcp.tool
def list_tickets(status: str | None = None) -> list[dict[str, Any]]:
    """All tickets on the board (tickets table), optionally filtered by status ('open', 'resolved', ...)."""
    with db() as conn:
        return rows(conn, 'SELECT * FROM tickets WHERE (? IS NULL OR status = ?) ORDER BY id', (status, status))


@mcp.tool
def get_desk() -> dict[str, Any]:
    """The shop's desk (desk table): date_today is 'today' for every overdue and lead-time decision."""
    with db() as conn:
        return one(conn, 'SELECT * FROM desk') or {}


@mcp.tool
def get_pricing(sku: str, qty: int = 1, discount_pct: float = 0.0) -> dict[str, Any]:
    """Unit cost and list price for a SKU (pricing table), with margin math.

    Give qty and an optional discount_pct (e.g. 10 for 10% off list) to get the
    discounted unit price, revenue, cost, and margin for that order, so nobody does
    margin arithmetic by hand.
    """
    if not 0 <= discount_pct < 100:
        raise ToolError('discount_pct must be between 0 and 100.')
    with db() as conn:
        p = one(conn, 'SELECT * FROM pricing WHERE sku = ?', (sku,))
    if p is None:
        raise ToolError(f'No pricing for sku={sku!r}.')
    unit_price = round(p['list_price'] * (1 - discount_pct / 100), 2)
    unit_margin = round(unit_price - p['unit_cost'], 2)
    return {
        **p,
        'list_margin_per_unit': round(p['list_price'] - p['unit_cost'], 2),
        'list_margin_pct': round((p['list_price'] - p['unit_cost']) / p['list_price'] * 100, 1),
        'qty': qty,
        'discount_pct': discount_pct,
        'discounted_unit_price': unit_price,
        'margin_per_unit': unit_margin,
        'margin_pct': round(unit_margin / unit_price * 100, 1) if unit_price else None,
        'order_revenue': round(unit_price * qty, 2),
        'order_cost': round(p['unit_cost'] * qty, 2),
        'order_margin': round(unit_margin * qty, 2),
        'sells_below_cost': unit_price < p['unit_cost'],
    }


@mcp.tool
def list_vendors() -> list[dict[str, Any]]:
    """Every vendor (vendors table) with lead_days and whether an open unpaid invoice blocks new shipments."""
    with db() as conn:
        vendors = rows(conn, 'SELECT * FROM vendors ORDER BY id')
        t = today(conn)
        for v in vendors:
            unpaid = open_invoices_for(conn, v['id'])
            v['open_invoices'] = unpaid
            v['blocked_by_unpaid_invoice'] = bool(unpaid)
            v['earliest_arrival_if_ordered_today'] = date.fromordinal(t.toordinal() + v['lead_days']).isoformat()
    return vendors


@mcp.tool
def get_invoice(invoice_id: int) -> dict[str, Any]:
    """Read one invoice (invoices table) with its vendor and days overdue relative to desk.date_today."""
    with db() as conn:
        inv = one(conn, 'SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        if inv is None:
            raise ToolError(f'No invoice with id {invoice_id}.')
        vendor = one(conn, 'SELECT * FROM vendors WHERE id = ?', (inv['vendor_id'],))
        t = today(conn)
        payments = rows(conn, "SELECT * FROM payments WHERE kind = 'invoice' AND ref_id = ?", (invoice_id,))
    days = (t - date.fromisoformat(inv['due_date'])).days
    return {
        'invoice': inv,
        'vendor': vendor,
        'date_today': t.isoformat(),
        'days_overdue': max(days, 0),
        'is_overdue': inv['status'] != 'paid' and days > 0,
        'payments_recorded': payments,
    }


@mcp.tool
def list_open_invoices() -> list[dict[str, Any]]:
    """All invoices not yet paid (invoices table), with vendor name and days overdue."""
    with db() as conn:
        t = today(conn)
        out = rows(
            conn,
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status != 'paid' ORDER BY i.due_date",
        )
    for inv in out:
        inv['days_overdue'] = max((t - date.fromisoformat(inv['due_date'])).days, 0)
    return out


@mcp.tool
def get_cash_balance(account: str = 'checking') -> dict[str, Any]:
    """Current balance of a cash account (cash_accounts table). Cash outflows only; no revenue is modeled."""
    with db() as conn:
        acct = one(conn, 'SELECT * FROM cash_accounts WHERE name = ?', (account,))
    if acct is None:
        raise ToolError(f'No cash account named {account!r}.')
    return {'account': acct['name'], 'balance': acct['balance'], 'as_of': acct['date']}


@mcp.tool
def list_payments() -> list[dict[str, Any]]:
    """Payments already made (payments table), newest first. Check here before proposing a payment."""
    with db() as conn:
        return rows(conn, 'SELECT * FROM payments ORDER BY id DESC')


@mcp.tool
def update_ticket_status(ticket_id: int, status: TicketStatus, note: str) -> dict[str, Any]:
    """Change a ticket's status on the board (tickets table) and append a short note explaining why.

    Only the Boss should use this, after deciding. Use 'awaiting_approval' when a
    payment still needs a person, and 'resolved' only when nothing is left to do.
    """
    with db() as conn:
        if one(conn, 'SELECT id FROM tickets WHERE id = ?', (ticket_id,)) is None:
            raise ToolError(f'No ticket with id {ticket_id}.')
        conn.execute(
            "UPDATE tickets SET status = ?, notes = COALESCE(notes, '') || ? WHERE id = ?",
            (status, f'\n[{status}] {note}', ticket_id),
        )
        conn.commit()
        return one(conn, 'SELECT * FROM tickets WHERE id = ?', (ticket_id,))


@mcp.tool
def save_board_draft(ticket_id: int, audience: Literal['customer', 'vendor', 'landlord', 'internal'], recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Save a message draft on the board (board_drafts table in the working database). It is never sent."""
    with db() as conn:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS board_drafts (id INTEGER PRIMARY KEY, ticket_id INTEGER, audience TEXT, '
            'recipient TEXT, subject TEXT, body TEXT, created_on TEXT)'
        )
        cur = conn.execute(
            'INSERT INTO board_drafts (ticket_id, audience, recipient, subject, body, created_on) VALUES (?, ?, ?, ?, ?, ?)',
            (ticket_id, audience, recipient, subject, body, today(conn).isoformat()),
        )
        conn.commit()
        return {'draft_id': cur.lastrowid, 'ticket_id': ticket_id, 'sent': False, 'note': 'Saved on the board only. Nothing was emailed.'}


# ---------------------------------------------------------------------------
# Human-only: hidden from every agent; only the backend's approve route calls it
# ---------------------------------------------------------------------------


@mcp.tool
def execute_approved_payment(
    approval_id: str,
    kind: Literal['invoice', 'rent', 'purchase_order'],
    amount: float,
    pay_from_account: str = 'checking',
    ref_id: int | None = None,
    vendor_id: int | None = None,
    sku: str | None = None,
    size: str | None = None,
    qty: int | None = None,
    approved_by: str = 'dashboard user',
) -> dict[str, Any]:
    """Execute a payment a person has approved on the dashboard. Rejects it if cash would go negative.

    invoice: ref_id = invoice id; amount must equal the invoice amount; marks the invoice paid.
    rent: ref_id = lease id; amount must equal monthly_rent; moves next_due forward one month.
    purchase_order: vendor_id, sku, size, qty; amount must equal unit_cost * qty; vendor must not be blocked.
    All kinds: subtracts the amount from the account and records a row in payments.
    """
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ToolError('Amount must be positive.')
    with db() as conn:
        acct = one(conn, 'SELECT * FROM cash_accounts WHERE name = ?', (pay_from_account,))
        if acct is None:
            raise ToolError(f'No cash account named {pay_from_account!r}.')
        t = today(conn)
        updates: list[tuple[str, tuple]] = []

        if kind == 'invoice':
            inv = one(conn, 'SELECT * FROM invoices WHERE id = ?', (ref_id,))
            if inv is None:
                raise ToolError(f'No invoice with id {ref_id}.')
            if inv['status'] == 'paid':
                raise ToolError(f'Invoice {ref_id} is already paid.')
            if round(inv['amount'], 2) != amount:
                raise ToolError(f'Amount {amount:.2f} does not match invoice {ref_id} amount {inv["amount"]:.2f}.')
            updates.append(("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,)))
        elif kind == 'rent':
            lease = one(conn, 'SELECT * FROM leases WHERE id = ?', (ref_id,))
            if lease is None:
                raise ToolError(f'No lease with id {ref_id}.')
            if round(lease['monthly_rent'], 2) != amount:
                raise ToolError(f'Amount {amount:.2f} does not match monthly rent {lease["monthly_rent"]:.2f} for lease {ref_id}.')
            due = date.fromisoformat(lease['next_due'])
            nxt = date(due.year + (due.month == 12), due.month % 12 + 1, min(due.day, 28))
            updates.append(('UPDATE leases SET next_due = ? WHERE id = ?', (nxt.isoformat(), ref_id)))
        else:
            if None in (vendor_id, sku, size, qty):
                raise ToolError('purchase_order needs vendor_id, sku, size, and qty.')
            if one(conn, 'SELECT id FROM vendors WHERE id = ?', (vendor_id,)) is None:
                raise ToolError(f'No vendor with id {vendor_id}.')
            if open_invoices_for(conn, vendor_id):
                raise ToolError(f'Vendor {vendor_id} has an open unpaid invoice and will not ship. Pay it first.')
            price = one(conn, 'SELECT * FROM pricing WHERE sku = ?', (sku,))
            if price is None:
                raise ToolError(f'No pricing for sku={sku!r}.')
            expected = round(price['unit_cost'] * qty, 2)
            if expected != amount:
                raise ToolError(f'Amount {amount:.2f} does not match unit_cost x qty = {expected:.2f}.')

        if acct['balance'] < amount:
            raise ToolError(
                f'Insufficient cash: {pay_from_account} has {acct["balance"]:.2f}, payment is {amount:.2f}. '
                'Payment rejected; balance cannot go negative.'
            )

        new_balance = round(acct['balance'] - amount, 2)
        try:
            for sql, params in updates:
                conn.execute(sql, params)
            conn.execute('UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?', (new_balance, t.isoformat(), pay_from_account))
            cur = conn.execute(
                'INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)',
                (kind, ref_id, amount, pay_from_account, t.isoformat(), f'{approved_by} (approval {approval_id})'),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return {
            'payment_id': cur.lastrowid,
            'kind': kind,
            'ref_id': ref_id,
            'amount': amount,
            'account': pay_from_account,
            'balance_before': acct['balance'],
            'balance_after': new_balance,
            'paid_at': t.isoformat(),
        }


if __name__ == '__main__':
    mcp.run(show_banner=False)
