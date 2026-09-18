import type { ModalityKey } from '@/config/modalities'
import { api } from './client'
import type {
  AIReview,
  FilterCatalog,
  FilterEfficiency,
  AnalysisPayload,
  Bet,
  BetsSummary,
  Draw,
  GameBatchSummary,
  GameInsight,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  ImportBatch,
  ImportSummary,
  PaginatedBets,
  PricingPreview,
  PricingTableRow,
} from './types'

export const endpoints = {
  health: () => api.get<HealthResponse>('/health'),

  pricingPreview: (modality: ModalityKey, numbers: number, games = 1, columnPicks?: number[]) => {
    const params = new URLSearchParams({ n: String(numbers), games: String(games) })
    if (columnPicks?.length) params.set('column_picks', columnPicks.join(','))
    return api.get<PricingPreview>(`/modalities/${modality}/pricing/preview?${params}`)
  },

  pricingTable: (modality: ModalityKey) =>
    api.get<{ modality: ModalityKey; rows: PricingTableRow[] }>(`/modalities/${modality}/pricing/table`),

  importDraws: (modality: ModalityKey, file: File) =>
    api.upload<ImportSummary>(`/modalities/${modality}/draws:import`, file),

  importBatches: (modality: ModalityKey) =>
    api.get<ImportBatch[]>(`/modalities/${modality}/import-batches`),

  draws: (modality: ModalityKey, limit = 20, offset = 0) =>
    api.get<{ items: Draw[]; total: number; limit: number; offset: number }>(
      `/modalities/${modality}/draws?limit=${limit}&offset=${offset}`,
    ),

  latestDraw: (modality: ModalityKey) => api.get<Draw>(`/modalities/${modality}/draws/latest`),

  filterCatalog: (modality: ModalityKey) =>
    api.get<FilterCatalog>(`/modalities/${modality}/filters`),

  filterEfficiency: (modality: ModalityKey, sample = 100) =>
    api.get<FilterEfficiency>(`/modalities/${modality}/filters/efficiency?sample=${sample}`),

  analysis: (modality: ModalityKey, refresh = false) =>
    api.get<AnalysisPayload>(`/modalities/${modality}/analysis?refresh=${refresh}`),

  generate: (modality: ModalityKey, body: GenerateRequest) =>
    api.post<GenerateResponse>(`/modalities/${modality}/games:generate`, body),

  gameInsight: (gameId: string) => api.get<GameInsight>(`/games/${gameId}/insight`),

  aiReview: (batchId: string) => api.post<AIReview>(`/game-batches/${batchId}/ai-review`),

  gameBatches: (modality?: ModalityKey, limit = 10) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (modality) params.set('modality', modality)
    return api.get<GameBatchSummary[]>(`/game-batches?${params}`)
  },

  createBet: (body: {
    game_id?: string
    modality?: ModalityKey
    contest_no: number
    numbers?: number[]
    extras?: Record<string, unknown>
    cost?: string
  }) => api.post<Bet>('/bets', body),

  bets: (params: { modality?: ModalityKey; status?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams()
    if (params.modality) query.set('modality', params.modality)
    if (params.status) query.set('status', params.status)
    query.set('limit', String(params.limit ?? 100))
    query.set('offset', String(params.offset ?? 0))
    return api.get<PaginatedBets>(`/bets?${query}`)
  },

  deleteBet: (betId: string) => api.del<void>(`/bets/${betId}`),

  checkBets: (modality?: ModalityKey) =>
    api.post<{ checked: number; skipped: number; results: Bet[] }>('/bets:check', {
      modality: modality ?? null,
    }),

  betsSummary: () => api.get<BetsSummary>('/bets/summary'),
}
