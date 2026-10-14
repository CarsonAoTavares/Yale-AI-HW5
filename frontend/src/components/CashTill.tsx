import { money } from '../agents'

interface Props {
  balance: number | null
  previous: number | null
  error: string | null
}

/** Checking balance. After an approved payment it shows the drop next to the new number. */
export function CashTill({ balance, previous, error }: Props) {
  const delta = balance !== null && previous !== null ? balance - previous : 0
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
      {delta !== 0 && (
        <div className={`till__delta ${delta < 0 ? 'down' : 'up'}`} key={`d${balance}`}>
          {delta < 0 ? '▼' : '▲'} {money(Math.abs(delta))} since last payment
        </div>
      )}
      <div className="till__foot">from cash_accounts · outflows only</div>
    </section>
  )
}
