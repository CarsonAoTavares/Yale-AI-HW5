import { AGENTS, AGENT_ORDER } from '../agents'
import type { AgentRole, TicketRunResult } from '../types'

/** After a run: one card per agent that took part, saying what it contributed. */
export function Contributions({ result }: { result: TicketRunResult }) {
  const { decision, delegations } = result
  const byAgent = new Map<AgentRole, string[]>()
  for (const d of delegations) {
    const notes = byAgent.get(d.to_agent) ?? []
    notes.push(d.error ? `Couldn't finish: ${d.error}` : d.result_summary ?? `Asked by ${AGENTS[d.from_agent].name}: ${d.task}`)
    byAgent.set(d.to_agent, notes)
  }

  return (
    <section className="contrib">
      <header className="contrib__head">
        <h3>Who did what</h3>
        <span className="muted">
          {result.requests} model calls · {result.total_tokens.toLocaleString()} tokens · {result.model}
        </span>
      </header>

      <div className="verdict" data-status={decision.status}>
        <div className="verdict__label">Boss's decision · {decision.status.replace('_', ' ')}</div>
        <p className="verdict__text">{decision.decision}</p>
        <p className="muted">{decision.reasoning}</p>
      </div>

      <div className="contrib__grid">
        {AGENT_ORDER.filter((r) => r !== 'boss' && byAgent.has(r)).map((role) => (
          <article key={role} className="card" style={{ '--agent': AGENTS[role].color } as React.CSSProperties}>
            <div className="card__who">
              <span className="avatar avatar--sm">{AGENTS[role].initials}</span>
              {AGENTS[role].name}
            </div>
            {byAgent.get(role)!.map((n, i) => <p key={i}>{n}</p>)}
          </article>
        ))}
        {byAgent.size === 0 && <p className="muted">The Boss handled this ticket without delegating.</p>}
      </div>

      {decision.drafts.length > 0 && (
        <div className="drafts">
          <h4>Drafts on the board (not sent)</h4>
          {decision.drafts.map((d, i) => (
            <details key={i} className="draft">
              <summary><span className="chip">{d.audience}</span> {d.subject} <span className="muted">to {d.recipient}</span></summary>
              <pre>{d.body}</pre>
            </details>
          ))}
        </div>
      )}

      {decision.next_steps.length > 0 && (
        <ul className="next">
          {decision.next_steps.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}
    </section>
  )
}
