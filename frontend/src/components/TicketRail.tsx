import type { Ticket } from '../types'

// Columns that might hold a human-readable headline. Whichever exists is used.
const TITLE_KEYS = ['title', 'subject', 'summary', 'type', 'category', 'description']

export function ticketTitle(t: Ticket): string {
  for (const k of TITLE_KEYS) if (typeof t[k] === 'string' && t[k]) return t[k] as string
  return `Ticket ${t.ticket_id}`
}

export function isResolved(t: Ticket, approvedRunIds: Set<string>): boolean {
  if (t.status?.toLowerCase() === 'resolved') return true
  const run = t.latest_run
  if (!run || run.status !== 'finished') return false
  if (run.decision_status === 'resolved') return true
  // Awaiting approval becomes resolved once a person approved its payments.
  return run.decision_status === 'awaiting_approval' && approvedRunIds.has(run.run_id)
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  onSelect: (id: number) => void
  approvedRunIds: Set<string>
}

export function TicketRail({ tickets, selectedId, onSelect, approvedRunIds }: Props) {
  return (
    <aside className="rail">
      <h2 className="rail__title">The Board</h2>
      <p className="rail__sub">{tickets.length} tickets on the desk</p>
      <ol className="rail__list">
        {tickets.map((t, i) => {
          const running = t.latest_run?.status === 'running'
          const resolved = isResolved(t, approvedRunIds)
          const state = running ? 'working' : resolved ? 'resolved' : t.latest_run?.decision_status ?? 'open'
          return (
            <li key={t.ticket_id} style={{ animationDelay: `${i * 70}ms` }}>
              <button
                className={`stub ${selectedId === t.ticket_id ? 'stub--active' : ''} ${resolved ? 'stub--resolved' : ''}`}
                onClick={() => onSelect(t.ticket_id)}
              >
                <span className="stub__no">#{t.ticket_id}</span>
                <span className="stub__title">{ticketTitle(t)}</span>
                <span className={`chip chip--${state}`}>
                  {running && <span className="pulse" />}
                  {state.replace('_', ' ')}
                </span>
                {resolved && <span className="stamp stamp--small">Resolved</span>}
              </button>
            </li>
          )
        })}
      </ol>
    </aside>
  )
}
