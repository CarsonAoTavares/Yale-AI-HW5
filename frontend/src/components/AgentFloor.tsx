import { AGENTS, AGENT_ORDER } from '../agents'
import type { AgentRole } from '../types'

interface Props {
  active: AgentRole | null
  involved: Set<AgentRole>
  running: boolean
}

/** The five agents as desks; the one currently thinking glows, ones that joined the ticket are lit. */
export function AgentFloor({ active, involved, running }: Props) {
  return (
    <div className="floor">
      {AGENT_ORDER.map((role) => {
        const a = AGENTS[role]
        const isActive = running && active === role
        const joined = involved.has(role)
        return (
          <div
            key={role}
            className={`desk ${isActive ? 'desk--active' : ''} ${joined ? 'desk--joined' : ''}`}
            style={{ '--agent': a.color } as React.CSSProperties}
          >
            <div className="avatar">{a.initials}</div>
            <div className="desk__name">{a.name}</div>
            <div className="desk__job">{isActive ? 'working…' : joined ? 'on this ticket' : a.job}</div>
          </div>
        )
      })}
    </div>
  )
}
