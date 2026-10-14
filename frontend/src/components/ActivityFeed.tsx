import { useEffect, useRef } from 'react'
import { AGENTS, time } from '../agents'
import type { ActivityEntry, AgentRole } from '../types'

function short(value: unknown, max = 280): string {
  const s = typeof value === 'string' ? value : JSON.stringify(value)
  if (!s) return ''
  return s.length > max ? `${s.slice(0, max)}…` : s
}

function who(agent: ActivityEntry['agent']) {
  return agent === 'human' ? { name: 'You', color: 'var(--ink)', initials: '✓' } : AGENTS[agent as AgentRole]
}

function Line({ e }: { e: ActivityEntry }) {
  const a = who(e.agent)
  const style = { '--agent': a?.color, marginLeft: `${Math.min(e.depth, 3) * 22}px` } as React.CSSProperties

  let body: React.ReactNode = null
  switch (e.event) {
    case 'agent_start':
      body = <><b>{a.name}</b> picked up: <q>{short(e.prompt, 220)}</q></>
      break
    case 'delegation': {
      const to = e.to_agent ? AGENTS[e.to_agent] : null
      body = (
        <>
          <b>{a.name}</b> <span className="arrow">→</span>{' '}
          <b style={{ color: to?.color }}>{to?.name}</b>: <q>{short(e.task, 260)}</q>
        </>
      )
      break
    }
    case 'model_response':
      body = (
        <>
          {e.text && <p className="say">{short(e.text, 500)}</p>}
          {(e.tool_calls ?? [])
            .filter((c) => c.tool !== 'delegate' && c.tool !== 'final_result')
            .map((c) => (
              <span key={c.tool_call_id} className="tool">
                <span className="tool__icon">⚙</span> {c.tool}
                <code>{short(c.args, 120)}</code>
              </span>
            ))}
          {(e.tool_calls ?? []).some((c) => c.tool === 'final_result') && <span className="muted">wrote up its report</span>}
          {!e.text && !(e.tool_calls ?? []).length && <span className="muted">thinking…</span>}
        </>
      )
      break
    case 'tool_result':
      if (e.tool === 'delegate') return null // the delegation line and agent_finish already show this
      body = <span className="result"><b>{e.tool}</b> returned <code>{short(e.output, 260)}</code></span>
      break
    case 'tool_retry':
      body = <span className="warn">Retrying {e.tool}: {short(e.message, 160)}</span>
      break
    case 'agent_finish':
      body = <><b>{a.name}</b> finished. <span className="muted">{short((e.output as { summary?: string; decision?: string })?.summary ?? (e.output as { decision?: string })?.decision, 260)}</span></>
      break
    case 'agent_error':
      body = <span className="warn"><b>{a.name}</b> hit an error: {e.error}</span>
      break
    case 'ticket_run_start':
      body = <span className="muted">Run started on {e.model}</span>
      break
    case 'ticket_run_finish':
      body = <span className="muted">Run finished: {String(e.status).replace('_', ' ')} · {String(e.total_tokens)} tokens</span>
      break
    default:
      body = <span className="muted">{e.event.replace(/_/g, ' ')}</span>
  }

  return (
    <li className={`line line--${e.event}`} style={style}>
      <span className="line__dot" />
      <div className="line__body">{body}</div>
      <time>{time(e.timestamp)}</time>
    </li>
  )
}

export function ActivityFeed({ entries, running }: { entries: ActivityEntry[]; running: boolean }) {
  // Keep the newest line in view by scrolling the feed box itself, not the page.
  const box = useRef<HTMLOListElement>(null)
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: 'smooth' })
  }, [entries.length])

  if (!entries.length) {
    return <div className="empty">{running ? 'Waiting for the first agent to speak…' : 'No activity yet. Dispatch the team to watch them work.'}</div>
  }
  return (
    <ol className="feed" ref={box}>
      {entries.map((e, i) => <Line key={`${e.timestamp}-${i}`} e={e} />)}
      {running && <li className="line line--typing"><span className="typing"><i /><i /><i /></span></li>}
    </ol>
  )
}
