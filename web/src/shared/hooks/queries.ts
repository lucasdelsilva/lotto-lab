import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { MODALITIES, modalityFromSlug, type ModalityConfig, type ModalityKey } from '@/config/modalities'
import { endpoints } from '@/shared/api/endpoints'
import type { GenerateRequest } from '@/shared/api/types'

export const queryKeys = {
  health: ['health'] as const,
  analysis: (modality: ModalityKey) => ['analysis', modality] as const,
  draws: (modality: ModalityKey) => ['draws', modality] as const,
  latestDraw: (modality: ModalityKey) => ['draws', modality, 'latest'] as const,
  importBatches: (modality: ModalityKey) => ['import-batches', modality] as const,
  pricing: (modality: ModalityKey, numbers: number, games: number) =>
    ['pricing', modality, numbers, games] as const,
  filterCatalog: (modality: ModalityKey) => ['filters', modality] as const,
  filterEfficiency: (modality: ModalityKey) => ['filters', modality, 'efficiency'] as const,
  gameBatches: (modality?: ModalityKey) => ['game-batches', modality ?? 'all'] as const,
  insight: (gameId: string) => ['insight', gameId] as const,
  bets: (modality?: ModalityKey) => ['bets', modality ?? 'all'] as const,
  betsSummary: ['bets', 'summary'] as const,
}

/** Resolve a modalidade da rota /m/:modality e devolve a config que dirige a tela. */
export function useModalityConfig(): ModalityConfig {
  const { modality } = useParams<{ modality: string }>()
  return modalityFromSlug(modality) ?? MODALITIES.MEGA_SENA
}

export function useHealth() {
  return useQuery({ queryKey: queryKeys.health, queryFn: endpoints.health, staleTime: 30_000 })
}

export function useAnalysis(modality: ModalityKey) {
  return useQuery({
    queryKey: queryKeys.analysis(modality),
    queryFn: () => endpoints.analysis(modality),
    retry: false,
    staleTime: 5 * 60_000,
  })
}

export function useLatestDraw(modality: ModalityKey) {
  return useQuery({
    queryKey: queryKeys.latestDraw(modality),
    queryFn: () => endpoints.latestDraw(modality),
    retry: false,
  })
}

export function useDraws(modality: ModalityKey, limit = 20) {
  return useQuery({
    queryKey: [...queryKeys.draws(modality), limit],
    queryFn: () => endpoints.draws(modality, limit),
    retry: false,
  })
}

export function useImportBatches(modality: ModalityKey) {
  return useQuery({
    queryKey: queryKeys.importBatches(modality),
    queryFn: () => endpoints.importBatches(modality),
  })
}

export function useImportDraws(modality: ModalityKey) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => endpoints.importDraws(modality, file),
    onSuccess: () => {
      // A importacao substitui o historico inteiro, entao tudo que deriva dele cai.
      void client.invalidateQueries({ queryKey: queryKeys.analysis(modality) })
      void client.invalidateQueries({ queryKey: queryKeys.draws(modality) })
      void client.invalidateQueries({ queryKey: queryKeys.importBatches(modality) })
    },
  })
}

export function usePricingPreview(
  modality: ModalityKey,
  numbers: number,
  games: number,
  columnPicks?: number[],
) {
  return useQuery({
    queryKey: [...queryKeys.pricing(modality, numbers, games), columnPicks?.join(',') ?? ''],
    queryFn: () => endpoints.pricingPreview(modality, numbers, games, columnPicks),
    retry: false,
    staleTime: 60_000,
  })
}

export function useFilterCatalog(modality: ModalityKey) {
  return useQuery({
    queryKey: queryKeys.filterCatalog(modality),
    queryFn: () => endpoints.filterCatalog(modality),
    staleTime: Infinity,
  })
}

export function useFilterEfficiency(modality: ModalityKey, sample = 100) {
  return useQuery({
    queryKey: [...queryKeys.filterEfficiency(modality), sample],
    queryFn: () => endpoints.filterEfficiency(modality, sample),
    retry: false,
    staleTime: 5 * 60_000,
  })
}

export function useGenerator(modality: ModalityKey) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: GenerateRequest) => endpoints.generate(modality, body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.gameBatches(modality) })
      void client.invalidateQueries({ queryKey: queryKeys.gameBatches() })
    },
  })
}

export function useGameInsight(gameId: string | null) {
  return useQuery({
    queryKey: queryKeys.insight(gameId ?? 'none'),
    queryFn: () => endpoints.gameInsight(gameId as string),
    enabled: Boolean(gameId),
  })
}

export function useGameBatches(modality?: ModalityKey, limit = 10) {
  return useQuery({
    queryKey: [...queryKeys.gameBatches(modality), limit],
    queryFn: () => endpoints.gameBatches(modality, limit),
  })
}

export function useBets(modality?: ModalityKey) {
  return useQuery({
    queryKey: queryKeys.bets(modality),
    queryFn: () => endpoints.bets({ modality }),
  })
}

export function useBetsSummary() {
  return useQuery({ queryKey: queryKeys.betsSummary, queryFn: endpoints.betsSummary })
}

export function useCreateBet() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: endpoints.createBet,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['bets'] })
    },
  })
}

export function useDeleteBet() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (betId: string) => endpoints.deleteBet(betId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['bets'] })
    },
  })
}

export function useCheckBets() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (modality?: ModalityKey) => endpoints.checkBets(modality),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['bets'] })
    },
  })
}

export function useAIReview() {
  return useMutation({ mutationFn: (batchId: string) => endpoints.aiReview(batchId) })
}
