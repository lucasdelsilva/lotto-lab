import type { ModalityKey } from '@/config/modalities'

export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail: string
  code: string
  instance: string
  request_id: string
  errors?: RowError[]
  total_cost?: string
  budget_limit?: string
  per_game?: string
}

export interface RowError {
  row: number
  field: string
  message: string
  value: string | null
}

export interface HealthResponse {
  status: string
  app: string
  environment: string
  database: { connected: boolean; error: string | null }
  ai_available: boolean
}

export interface PricingPreview {
  modality: ModalityKey
  numbers: number
  combinations: number
  base_price: string
  per_game: string
  total: string
  games: number
  column_picks: number[] | null
}

export interface PricingTableRow {
  numbers: number
  combinations: number
  price: string
  column_picks: number[] | null
}

export interface ImportSummary {
  batch_id: string
  modality: ModalityKey
  filename: string
  file_hash: string
  rows_imported: number
  rows_deleted: number
  first_contest: number | null
  last_contest: number | null
  first_drawn_at: string | null
  last_drawn_at: string | null
  imported_at: string
}

export interface ImportBatch {
  id: string
  modality: ModalityKey
  filename: string
  file_hash: string
  rows_imported: number
  first_contest: number | null
  last_contest: number | null
  first_drawn_at: string | null
  last_drawn_at: string | null
  imported_at: string
  status: string
}

export interface Draw {
  contest_no: number
  drawn_at: string
  numbers: number[]
  extras: Record<string, unknown>
}

export interface HistoryMeta {
  total_draws: number
  first_contest: number
  last_contest: number
  first_drawn_at: string | null
  last_drawn_at: string | null
}

export interface NumberStat {
  n: number
  freq: number
  freq_rate: number
  temperature: 'hot' | 'cold' | 'neutral'
  current_delay: number
  avg_delay: number
  max_delay: number
  delay_ratio: number
  [key: `z_${number}`]: number | string | undefined
}

export interface MonthStat {
  month: number
  count: number
  rate: number
  current_delay: number
}

export interface MetricRange {
  p10: number
  p25: number
  p50: number
  p75: number
  p90: number
  min?: number
  max?: number
  mean?: number
}

export interface PatternReport {
  ranges: Record<string, MetricRange>
  sum_histogram: { start: number; end: number; count: number }[]
  even_distribution: { even: number; count: number }[]
  quadrant_totals: number[]
  ending_totals: number[]
}

export interface SequenceReport {
  max_consecutive: { histogram: { value: number; count: number }[]; mean: number; p90: number }
  repeat_from_previous: {
    histogram: { value: number; count: number }[]
    mean: number
    p10: number
    p50: number
    p90: number
  }
  last_draw: number[]
}

export interface PairEntry {
  pair: [number, number]
  count: number
  lift: number
}

export interface SuperSeteReport {
  window: number
  columns: {
    frequency: number[][]
    relative: number[][]
    z_scores: number[][]
    current_delay: number[][]
    average_delay: number[][]
    delay_ratio: number[][]
  }
  sum_distribution: {
    histogram: { value: number; count: number }[]
    p10: number
    p50: number
    p90: number
    mean: number
  }
  repeated_digits: { repeated: number; count: number }[]
  adjacent_sequences: { adjacent: number; count: number }[]
  repeated_results: { result: number[]; contests: number[] }[]
  last_draw: number[]
}

export interface AnalysisPayload {
  modality: ModalityKey
  computed_at: string
  window: number
  cached: boolean
  history_meta: HistoryMeta
  numbers?: NumberStat[]
  delay_heatmap?: number[][]
  patterns?: PatternReport
  sequences?: SequenceReport
  pairs?: { top_pairs: PairEntry[]; never_together: number[][] }
  triples?: { triple: number[]; count: number }[]
  months?: MonthStat[]
  supersete?: SuperSeteReport
}

export type GeneratorProfile = 'balanced' | 'hot' | 'cold' | 'pattern' | 'uniform'

export type FilterId =
  | 'even_odd'
  | 'sum'
  | 'rows'
  | 'columns'
  | 'repeated'
  | 'consecutive'
  | 'gaps'
  | 'fibonacci'
  | 'primes'
  | 'pareto'
  | 'weights'

export interface FilterDefinition {
  id: FilterId
  label: string
  description: string
  default_enabled: boolean
}

export interface FilterCatalog {
  modality: ModalityKey
  filters: FilterDefinition[]
}

export interface FilterEfficiencyRow {
  id: FilterId
  label: string
  approved: number
  total: number
  efficiency: number
}

export interface FilterEfficiency {
  modality: ModalityKey
  sample: number
  filters: FilterEfficiencyRow[]
  overall: number
  bounds: Record<string, unknown>
}

export interface GeneratorFilters {
  enabled: FilterId[]
  max_consecutive: number | null
  min_quadrants_covered: number
  /** O gerador descarta e refaz o jogo cuja combinacao ja saiu; flag apenas marca. */
  on_already_drawn: 'flag' | 'reject'
}

export interface GenerateRequest {
  numbers_per_game: number
  games: number
  profile: GeneratorProfile
  seed: number | null
  budget_limit: number | null
  filters: GeneratorFilters
  extras?: { month_strategy?: 'auto' | 'fixed' | 'random'; month?: number | null }
  max_overlap?: number | null
}

export interface GameSummary {
  id: string
  numbers: number[]
  already_drawn: boolean
  extras: { columns?: number[][]; month?: number } | null
}

export interface GenerateResponse {
  batch_id: string
  modality: ModalityKey
  seed: number
  games: GameSummary[]
  cost: { per_game: string; total: string; within_budget: boolean }
}

export interface GameInsight {
  id: string
  batch_id: string
  modality: ModalityKey
  numbers: number[]
  extras: Record<string, unknown>
  engine_score: number
  already_drawn: boolean
  matched_contests: number[]
  metrics: {
    sum: number
    even: number
    odd: number
    primes: number
    spread: number
    max_consecutive: number
    consecutive_pairs: number
    quadrants: number[]
    endings: Record<string, number>
    multiples_of_3: number
    multiples_of_5: number
    mean: number
    median: number
  }
  pattern_ranges: Record<string, MetricRange>
  fit_score: number
  best_historical_match: { contest: number | null; hits: number }
  drawn_subsets: { numbers: number[]; contests: number[] }[]
  hot_numbers_used: number[]
  cold_numbers_used: number[]
  overdue_numbers_used: number[]
}

export interface GameBatchSummary {
  batch_id: string
  modality: ModalityKey
  created_at: string
  profile: GeneratorProfile
  games_count: number
  numbers_per_game: number
  total_cost: string
}

export interface BetResult {
  hits: number
  extra_hit: boolean
  prize: string
  checked_at: string
}

export interface Bet {
  id: string
  game_id: string | null
  modality: ModalityKey
  contest_no: number
  numbers: number[]
  extras: Record<string, unknown>
  cost: string
  placed_at: string
  status: 'PENDING' | 'CHECKED' | 'CANCELLED'
  result: BetResult | null
}

export interface PaginatedBets {
  items: Bet[]
  total: number
  limit: number
  offset: number
}

export interface BetsSummary {
  rows: {
    modality: ModalityKey
    month: string
    bets: number
    spent: string
    returned: string
    balance: string
  }[]
  total_spent: string
  total_returned: string
  balance: string
}

export interface AIReview {
  batch_id: string
  ai_available: boolean
  model: string | null
  tokens: { prompt: number; completion: number; total: number } | null
  error: string | null
  analysis: {
    overview: string
    history_reading: {
      hot_numbers: { n: number; evidence: string }[]
      cold_numbers: { n: number; evidence: string }[]
      overdue_numbers: { n: number; delay_ratio: number }[]
      pattern_notes: string[]
      sequence_notes: string[]
    }
    ranked_games: {
      id: string
      rank: number
      statistical_fit: number
      already_drawn: boolean
      rationale: string
    }[]
    set_diagnostics: { avg_overlap: number; coverage: number[]; warnings: string[] }
    budget: { total_cost: number; within_limit: boolean; note: string }
    disclaimer: string
  } | null
}
