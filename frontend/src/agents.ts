import type { AgentRole } from './types'

export interface AgentMeta {
  role: AgentRole
  name: string
  initials: string
  job: string
  color: string
}

export const AGENTS: Record<AgentRole, AgentMeta> = {
  boss: { role: 'boss', name: 'Boss', initials: 'BO', job: 'Assigns work, makes the call', color: 'var(--boss)' },
  inventory: { role: 'inventory', name: 'Inventory', initials: 'IN', job: 'Stock, shortages, vendors', color: 'var(--inventory)' },
  accounting: { role: 'accounting', name: 'Accounting', initials: 'AC', job: 'Cash, invoices, approvals', color: 'var(--accounting)' },
  facilities: { role: 'facilities', name: 'Facilities', initials: 'FA', job: 'Leases and rent', color: 'var(--facilities)' },
  customer_service: { role: 'customer_service', name: 'Customer Service', initials: 'CS', job: 'Customer drafts', color: 'var(--cs)' },
}

export const AGENT_ORDER: AgentRole[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
