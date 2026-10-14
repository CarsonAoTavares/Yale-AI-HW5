// Shapes returned by the FastAPI backend (backend/main.py, backend/models.py).

export type AgentRole = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type DecisionStatus = 'resolved' | 'awaiting_approval' | 'blocked' | 'needs_info'

export interface RunSummary {
  run_id: string
  ticket_id: number
  status: 'running' | 'finished' | 'failed'
  started_at: string
  finished_at: string | null
  error: string | null
  decision_status?: DecisionStatus | null
}

// Ticket columns come straight from the tickets table via MCP, so only the
// fields the board relies on are typed; the rest are shown as-is.
export interface Ticket {
  ticket_id: number
  status?: string
  latest_run: RunSummary | null
  [column: string]: unknown
}

export interface Finding {
  fact: string
  source: string
}

export interface ApprovalRequest {
  kind: 'invoice' | 'rent' | 'purchase_order'
  ticket_id: number | null
  payee: string
  amount: number
  pay_from_account: string
  ref_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  reason: string
  cash_check: string
}

export interface DraftMessage {
  audience: 'customer' | 'vendor' | 'landlord' | 'internal'
  ticket_id: number | null
  recipient: string
  subject: string
  body: string
}

export interface TicketDecision {
  ticket_id: number
  status: DecisionStatus
  decision: string
  reasoning: string
  agents_consulted: AgentRole[]
  findings: Finding[]
  approvals_needed: ApprovalRequest[]
  drafts: DraftMessage[]
  next_steps: string[]
}

export interface DelegationRecord {
  from_agent: AgentRole
  to_agent: AgentRole
  task: string
  depth: number
  result_summary: string | null
  error: string | null
}

export interface TicketRunResult {
  decision: TicketDecision
  delegations: DelegationRecord[]
  model: string
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

export interface RunState extends RunSummary {
  result: TicketRunResult | null
}

export interface ToolCall {
  tool: string
  tool_call_id: string
  args: unknown
}

export interface ActivityEntry {
  timestamp: string
  run_id: string
  ticket_id: number | null
  agent: AgentRole | 'human'
  depth: number
  event: string
  prompt?: string
  task?: string
  to_agent?: AgentRole
  text?: string | null
  tool_calls?: ToolCall[]
  tool?: string
  output?: unknown
  message?: unknown
  error?: string
  model?: string
  [key: string]: unknown
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'failed' | 'void'

export interface StoredApproval {
  id: string
  run_id: string
  ticket_id: number | null
  created_at: string
  status: ApprovalStatus
  request: ApprovalRequest
  decided_at: string | null
  result: unknown
}
