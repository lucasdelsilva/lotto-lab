/**
 * Espelho de MODALITY_RULES do back. Toda a tela de modalidade e dirigida por este
 * arquivo: volante, cores, limites e campos extras saem daqui, e nao de cinco telas
 * duplicadas. O Super Sete e a unica excecao estrutural, e por isso declara o proprio
 * componente de volante em `boardKind`.
 */

export const MODALITY_KEYS = [
  'MEGA_SENA',
  'LOTOFACIL',
  'QUINA',
  'DIA_DE_SORTE',
  'SUPER_SETE',
] as const

export type ModalityKey = (typeof MODALITY_KEYS)[number]

export type BoardKind = 'numbers' | 'columns'

export interface ModalityConfig {
  key: ModalityKey
  label: string
  tagline: string
  slug: string
  color: string
  accent: string
  universeMin: number
  universeMax: number
  minPick: number
  maxPick: number
  baseHits: number
  basePrice: number
  boardKind: BoardKind
  boardRows: number
  boardCols: number
  columns: number
  columnMinPick: number
  columnMaxPick: number
  extraField: 'month' | null
  extraLabel: string | null
}

export const MODALITIES: Record<ModalityKey, ModalityConfig> = {
  MEGA_SENA: {
    key: 'MEGA_SENA',
    label: 'Mega-Sena',
    tagline: 'A loteria que paga milhoes para quem acerta os seis numeros sorteados.',
    slug: 'mega-sena',
    color: '#209869',
    accent: '#0b6b48',
    universeMin: 1,
    universeMax: 60,
    minPick: 6,
    maxPick: 20,
    baseHits: 6,
    basePrice: 6,
    boardKind: 'numbers',
    boardRows: 6,
    boardCols: 10,
    columns: 0,
    columnMinPick: 0,
    columnMaxPick: 0,
    extraField: null,
    extraLabel: null,
  },
  LOTOFACIL: {
    key: 'LOTOFACIL',
    label: 'Lotofacil',
    tagline: 'Escolha de 15 a 20 numeros entre os 25 disponiveis e ganhe de 11 a 15 acertos.',
    slug: 'lotofacil',
    color: '#930989',
    accent: '#6b0664',
    universeMin: 1,
    universeMax: 25,
    minPick: 15,
    maxPick: 20,
    baseHits: 15,
    basePrice: 3.5,
    boardKind: 'numbers',
    boardRows: 5,
    boardCols: 5,
    columns: 0,
    columnMinPick: 0,
    columnMaxPick: 0,
    extraField: null,
    extraLabel: null,
  },
  QUINA: {
    key: 'QUINA',
    label: 'Quina',
    tagline: 'Seis sorteios na semana e muitas chances de ganhar.',
    slug: 'quina',
    color: '#260085',
    accent: '#180058',
    universeMin: 1,
    universeMax: 80,
    minPick: 5,
    maxPick: 15,
    baseHits: 5,
    basePrice: 3,
    boardKind: 'numbers',
    boardRows: 8,
    boardCols: 10,
    columns: 0,
    columnMinPick: 0,
    columnMaxPick: 0,
    extraField: null,
    extraLabel: null,
  },
  DIA_DE_SORTE: {
    key: 'DIA_DE_SORTE',
    label: 'Dia de Sorte',
    tagline: 'Seu dia pode ser uma otima inspiracao para a sorte. Aposte!',
    slug: 'dia-de-sorte',
    color: '#CB8E4E',
    accent: '#8f6233',
    universeMin: 1,
    universeMax: 31,
    minPick: 7,
    maxPick: 15,
    baseHits: 7,
    basePrice: 2.5,
    boardKind: 'numbers',
    boardRows: 4,
    boardCols: 8,
    columns: 0,
    columnMinPick: 0,
    columnMaxPick: 0,
    extraField: 'month',
    extraLabel: 'Mes da Sorte',
  },
  SUPER_SETE: {
    key: 'SUPER_SETE',
    label: 'Super Sete',
    tagline: 'Aposte no Super Sete e concorra a premios em tres sorteios semanais.',
    slug: 'super-sete',
    color: '#A8CF45',
    accent: '#6f8f1f',
    universeMin: 0,
    universeMax: 9,
    minPick: 7,
    maxPick: 21,
    baseHits: 7,
    basePrice: 3,
    boardKind: 'columns',
    boardRows: 10,
    boardCols: 7,
    columns: 7,
    columnMinPick: 1,
    columnMaxPick: 3,
    extraField: null,
    extraLabel: null,
  },
}

export const MODALITY_LIST: ModalityConfig[] = MODALITY_KEYS.map((key) => MODALITIES[key])

export const MONTH_NAMES = [
  'Janeiro',
  'Fevereiro',
  'Marco',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
] as const

export const MONTH_ABBR = [
  'JAN',
  'FEV',
  'MAR',
  'ABR',
  'MAI',
  'JUN',
  'JUL',
  'AGO',
  'SET',
  'OUT',
  'NOV',
  'DEZ',
] as const

export function modalityFromSlug(slug: string | undefined): ModalityConfig | null {
  if (!slug) return null
  const normalized = slug.toLowerCase()
  const bySlug = MODALITY_LIST.find((item) => item.slug === normalized)
  if (bySlug) return bySlug
  const byKey = MODALITY_LIST.find((item) => item.key.toLowerCase() === normalized)
  return byKey ?? null
}

/** Universo completo da modalidade, na ordem do volante. */
export function universeOf(config: ModalityConfig): number[] {
  const size = config.universeMax - config.universeMin + 1
  return Array.from({ length: size }, (_, index) => config.universeMin + index)
}
