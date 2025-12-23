import { api } from './chat-api'

// Proposal Types
export interface ProposalFile {
  id: string
  file_path: string
  operation: 'create' | 'modify' | 'delete'
  original_content?: string
  proposed_content?: string  // API returns proposed_content, not new_content
  diff_hunks?: DiffHunk[]
}

export interface DiffHunk {
  old_start: number
  old_count: number
  new_start: number
  new_count: number
  lines: string[]
}

export interface Proposal {
  id: string
  session_id: string
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  description: string
  created_at: string
  applied_at?: string
  backup_id?: string
  files: ProposalFile[]
}

export interface ProposalSummary {
  id: string
  session_id: string
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  description: string
  created_at: string
  file_count: number
}

// API Functions
export async function getProposals(status?: string): Promise<ProposalSummary[]> {
  const params = status ? { status } : {}
  const response = await api.get<ProposalSummary[]>('/proposals', { params })
  return response.data
}

export async function getProposal(proposalId: string): Promise<Proposal> {
  const response = await api.get<Proposal>(`/proposals/${proposalId}`)
  return response.data
}

export async function approveProposal(proposalId: string): Promise<Proposal> {
  const response = await api.post<Proposal>(`/proposals/${proposalId}/approve`)
  return response.data
}

export async function rejectProposal(proposalId: string): Promise<Proposal> {
  const response = await api.post<Proposal>(`/proposals/${proposalId}/reject`)
  return response.data
}
