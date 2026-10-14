import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, readBalance } from './api'
import { AGENTS } from './agents'
import { ActivityFeed } from './components/ActivityFeed'
import { AgentFloor } from './components/AgentFloor'
import { ApprovalInbox } from './components/ApprovalInbox'
import { CashTill } from './components/CashTill'
import { Contributions } from './components/Contributions'
import { TicketRail, isResolved, ticketTitle } from './components/TicketRail'
import type { ActivityEntry, AgentRole, RunState, StoredApproval, Ticket } from './types'

const POLL_MS = 1200
const HIDDEN_FIELDS = new Set(['ticket_id', 'latest_run'])

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [ticketsError, setTicketsError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [run, setRun] = useState<RunState | null>(null)
  const [activity, setActivity] = useState<ActivityEntry[]>([])
  const [approvals, setApprovals] = useState<StoredApproval[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  const [prevBalance, setPrevBalance] = useState<number | null>(null)
  const [cashError, setCashError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const flash = (msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), 4000)
  }

  const loadTickets = useCallback(async () => {
    try {
      const t = await api.tickets()
      setTickets(t)
      setTicketsError(null)
      setSelectedId((id) => id ?? t[0]?.ticket_id ?? null)
    } catch (e) {
      setTicketsError((e as Error).message)
    }
  }, [])

  const loadCash = useCallback(async (afterPayment = false) => {
    try {
      const b = readBalance(await api.cash())
      setBalance((old) => {
        if (afterPayment) setPrevBalance(old)
        return b
      })
      setCashError(b === null ? 'The cash tool returned no balance field.' : null)
    } catch (e) {
      setCashError((e as Error).message)
    }
  }, [])

  const loadApprovals = useCallback(async () => {
    try {
      setApprovals(await api.approvals())
    } catch {
      /* the inbox just stays as it was */
    }
  }, [])

  useEffect(() => {
    loadTickets()
    loadCash()
    loadApprovals()
  }, [loadTickets, loadCash, loadApprovals])

  const selected = tickets.find((t) => t.ticket_id === selectedId) ?? null

  // When switching tickets, show that ticket's latest run (if any).
  useEffect(() => {
    const runId = selected?.latest_run?.run_id
    if (!runId) {
      setRun(null)
      setActivity([])
      return
    }
    if (run?.run_id === runId) return
    api.run(runId).then(setRun).catch(() => setRun(null))
    api.activity(runId).then((a) => setActivity(a.reverse())).catch(() => setActivity([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, selected?.latest_run?.run_id])

  // Live polling while the team is working.
  useEffect(() => {
    if (run?.status !== 'running') return
    const id = window.setInterval(async () => {
      try {
        const [state, feed] = await Promise.all([api.run(run.run_id), api.activity(run.run_id)])
        setActivity(feed.reverse())
        if (state.status !== 'running') {
          setRun(state)
          loadTickets()
          loadApprovals()
          flash(state.status === 'finished' ? `Ticket #${state.ticket_id}: ${state.result?.decision.status.replace('_', ' ')}` : `Run failed: ${state.error}`)
        }
      } catch {
        /* keep polling */
      }
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [run?.run_id, run?.status, loadTickets, loadApprovals])

  const dispatch = async () => {
    if (!selected) return
    try {
      const state = await api.runTicket(selected.ticket_id)
      setRun(state)
      setActivity([])
      loadTickets()
    } catch (e) {
      flash((e as Error).message)
    }
  }

  const approve = async (id: string) => {
    try {
      const a = await api.approve(id)
      flash(`Paid ${a.request.payee}.`)
      await loadCash(true)
    } catch (e) {
      flash(`Payment refused: ${(e as Error).message}`)
    }
    await Promise.all([loadApprovals(), loadTickets()])
  }

  const reject = async (id: string) => {
    await api.reject(id).catch((e) => flash((e as Error).message))
    await loadApprovals()
  }

  const reset = async () => {
    if (!window.confirm('Restore the working database to its original values? Pending approvals will be voided.')) return
    try {
      const r = await api.reset()
      flash(`Database restored. ${r.voided_approvals} pending request(s) voided.`)
      setRun(null)
      setActivity([])
      setPrevBalance(null)
      await Promise.all([loadTickets(), loadCash(), loadApprovals()])
    } catch (e) {
      flash((e as Error).message)
    }
  }

  const approvedRunIds = useMemo(() => {
    const byRun = new Map<string, StoredApproval[]>()
    approvals.forEach((a) => byRun.set(a.run_id, [...(byRun.get(a.run_id) ?? []), a]))
    return new Set([...byRun].filter(([, list]) => list.every((a) => a.status === 'approved')).map(([id]) => id))
  }, [approvals])

  const running = run?.status === 'running'
  const involved = useMemo(() => new Set(activity.map((e) => e.agent).filter((a): a is AgentRole => a in AGENTS)), [activity])
  const activeAgent = useMemo(() => {
    for (let i = activity.length - 1; i >= 0; i--) {
      const a = activity[i].agent
      if (a in AGENTS && activity[i].event !== 'agent_finish') return a as AgentRole
    }
    return 'boss' as AgentRole
  }, [activity])

  const resolved = selected ? isResolved(selected, approvedRunIds) : false
  const fields = selected ? Object.entries(selected).filter(([k, v]) => !HIDDEN_FIELDS.has(k) && v !== null && v !== '') : []

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark">CC</span>
          <div>
            <h1>Campus Customs</h1>
            <span className="brand__sub">Operations Desk</span>
          </div>
        </div>
        <div className="topbar__right">
          <span className="model-chip" title="Every agent runs on this model via Portkey">gpt-6-luna</span>
          <button className="btn btn--ghost" onClick={reset} disabled={running}>↺ Fresh run</button>
        </div>
      </header>

      <div className="layout">
        {ticketsError ? (
          <aside className="rail">
            <h2 className="rail__title">The Board</h2>
            <div className="empty empty--error">Can't load tickets.<small>{ticketsError}</small></div>
          </aside>
        ) : (
          <TicketRail tickets={tickets} selectedId={selectedId} onSelect={setSelectedId} approvedRunIds={approvedRunIds} />
        )}

        <main className="stage">
          {selected ? (
            <>
              <section className="casefile">
                {resolved && <span className="stamp stamp--big">Resolved</span>}
                <div className="casefile__no">Ticket #{selected.ticket_id}</div>
                <h2 className="casefile__title">{ticketTitle(selected)}</h2>
                <dl className="fields">
                  {fields.map(([k, v]) => (
                    <div key={k}><dt>{k.replace(/_/g, ' ')}</dt><dd>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd></div>
                  ))}
                </dl>
                <button className="btn btn--dispatch" onClick={dispatch} disabled={running}>
                  {running ? 'Team is working…' : run ? 'Run the team again' : 'Dispatch the team'}
                </button>
              </section>

              <AgentFloor active={activeAgent} involved={involved} running={running} />

              <section className="panel">
                <header className="panel__head">
                  <h3>Live floor</h3>
                  {running && <span className="live"><span className="pulse" /> live</span>}
                </header>
                <ActivityFeed entries={activity} running={running} />
              </section>

              {run?.status === 'finished' && run.result && <Contributions result={run.result} />}
              {run?.status === 'failed' && <div className="empty empty--error">The run failed.<small>{run.error}</small></div>}
            </>
          ) : (
            <div className="empty">Pick a ticket from the board.</div>
          )}
        </main>

        <aside className="side">
          <CashTill balance={balance} previous={prevBalance} error={cashError} />
          <ApprovalInbox approvals={approvals} onApprove={approve} onReject={reject} />
        </aside>
      </div>

      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  )
}
