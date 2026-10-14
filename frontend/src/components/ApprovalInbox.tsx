import { useState } from 'react'
import { money } from '../agents'
import type { ApprovalRequest, StoredApproval } from '../types'

interface Props {
  approvals: StoredApproval[]
  onApprove: (id: string) => Promise<void>
  onReject: (id: string) => Promise<void>
}

const KIND = { invoice: 'Invoice payment', rent: 'Rent payment', purchase_order: 'Purchase order' } as const

function describe(r: ApprovalRequest): string {
  if (r.kind === 'invoice') return `Invoice #${r.ref_id}`
  if (r.kind === 'rent') return `Lease #${r.ref_id} monthly rent`
  return `${r.qty} × ${r.sku} (${r.size}) from vendor #${r.vendor_id}`
}

const STAMP: Record<string, string> = { approved: 'Paid', rejected: 'Rejected', failed: 'Refused', void: 'Void' }

export function ApprovalInbox({ approvals, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<string | null>(null)
  const pending = approvals.filter((a) => a.status === 'pending')
  const decided = approvals.filter((a) => a.status !== 'pending').slice(-4).reverse()

  const act = async (id: string, fn: (id: string) => Promise<void>) => {
    setBusy(id)
    try {
      await fn(id)
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="inbox">
      <header className="inbox__head">
        <h3>Needs your signature</h3>
        {pending.length > 0 && <span className="badge">{pending.length}</span>}
      </header>
      <p className="muted small">Agents prepare payments. Nothing moves until you approve.</p>

      {pending.length === 0 && <div className="empty empty--small">No requests waiting.</div>}

      {pending.map((a) => (
        <article key={a.id} className="check">
          <div className="check__top">
            <span className="check__kind">{KIND[a.request.kind]}</span>
            <span className="muted">ticket #{a.ticket_id}</span>
          </div>
          <div className="check__payee">Pay to <b>{a.request.payee}</b></div>
          <div className="check__amount">{money(a.request.amount)}</div>
          <dl className="check__meta">
            <dt>For</dt><dd>{describe(a.request)}</dd>
            <dt>From</dt><dd>{a.request.pay_from_account}</dd>
            <dt>Why</dt><dd>{a.request.reason}</dd>
            <dt>Cash check</dt><dd>{a.request.cash_check}</dd>
          </dl>
          <div className="check__actions">
            <button className="btn btn--ghost" disabled={busy === a.id} onClick={() => act(a.id, onReject)}>Reject</button>
            <button className="btn btn--approve" disabled={busy === a.id} onClick={() => act(a.id, onApprove)}>
              {busy === a.id ? 'Paying…' : 'Approve'}
            </button>
          </div>
        </article>
      ))}

      {decided.length > 0 && (
        <ul className="history">
          {decided.map((a) => (
            <li key={a.id}>
              <span className={`stamp stamp--tiny stamp--${a.status}`}>{STAMP[a.status]}</span>
              <span>{a.request.payee}</span>
              <span className="mono">{money(a.request.amount)}</span>
              {a.status === 'failed' && <small className="warn">{String(a.result)}</small>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
