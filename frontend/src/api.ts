import type { ActivityEntry, RunState, StoredApproval, Ticket } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// The FastAPI backend (Problem 7). Its CORS settings allow this Vite page's origin.
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string) => request<T>(path, { method: 'POST' })

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  runTicket: (ticketId: number) => post<RunState>(`/tickets/${ticketId}/run`),
  run: (runId: string) => request<RunState>(`/runs/${runId}`),
  activity: (runId: string, limit = 400) => request<ActivityEntry[]>(`/activity?run_id=${runId}&limit=${limit}`),
  approvals: () => request<StoredApproval[]>('/approvals'),
  approve: (id: string) => post<StoredApproval>(`/approvals/${id}/approve`),
  reject: (id: string) => post<StoredApproval>(`/approvals/${id}/reject`),
  cash: () => request<unknown>('/cash'),
  reset: () => post<{ ok: boolean; voided_approvals: number }>('/reset'),
}

/** The cash route returns whatever the MCP tool returns; pull a number out of it without guessing. */
export function readBalance(raw: unknown): number | null {
  if (typeof raw === 'number') return raw
  if (raw && typeof raw === 'object') {
    for (const key of ['balance', 'current_balance', 'available_balance', 'amount']) {
      const v = (raw as Record<string, unknown>)[key]
      if (typeof v === 'number') return v
    }
  }
  return null
}
