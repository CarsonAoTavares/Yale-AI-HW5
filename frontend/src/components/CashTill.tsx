import { money } from '../agents'

interface Props {
  balance: number | null
  lastPayment: { before: number; after: number; label: string } | null
  error: string | null
}

/** Checking balance, plus the drop from the most recent approved payment (from the payment tool's own before/after). */
export function CashTill({ balance, lastPayment, error }: Props) {
  return (
    <section className="till">
      <div className="till__label">Checking account</div>
      {error ? (
        <div className="till__error">Balance unavailable<small>{error}</small></div>
      ) : balance === null ? (
        <div className="till__amount till__amount--loading">—</div>
      ) : (
        <div className="till__amount" key={balance}>{money(balance)}</div>
      )}
      {lastPayment && (
        <div className="till__delta down" key={`d${lastPayment.after}`}>
          ▼ {money(lastPayment.before - lastPayment.after)} · {lastPayment.label}
          <small>{money(lastPayment.before)} → {money(lastPayment.after)}</small>
        </div>
      )}
      <div className="till__foot">from cash_accounts · outflows only</div>
    </section>
  )
}
