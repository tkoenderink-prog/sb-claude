import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getProposals,
  getProposal,
  approveProposal,
  rejectProposal,
  type Proposal,
  type ProposalSummary,
} from '@/lib/proposal-api'

export function useProposals(status?: string) {
  return useQuery<ProposalSummary[]>({
    queryKey: ['proposals', status],
    queryFn: () => getProposals(status),
  })
}

export function useProposal(proposalId: string | null) {
  return useQuery<Proposal>({
    queryKey: ['proposal', proposalId],
    queryFn: () => getProposal(proposalId!),
    enabled: !!proposalId,
  })
}

export function useApproveProposal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (proposalId: string) => approveProposal(proposalId),
    onSuccess: (data) => {
      // Update the proposal in cache
      queryClient.setQueryData(['proposal', data.id], data)
      // Invalidate proposals list
      queryClient.invalidateQueries({ queryKey: ['proposals'] })
    },
  })
}

export function useRejectProposal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (proposalId: string) => rejectProposal(proposalId),
    onSuccess: (data) => {
      // Update the proposal in cache
      queryClient.setQueryData(['proposal', data.id], data)
      // Invalidate proposals list
      queryClient.invalidateQueries({ queryKey: ['proposals'] })
    },
  })
}
