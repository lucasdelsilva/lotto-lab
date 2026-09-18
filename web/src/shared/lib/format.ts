const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const decimal = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const integer = new Intl.NumberFormat('pt-BR')

export function formatMoney(value: string | number): string {
  const numeric = typeof value === 'string' ? Number(value) : value
  return Number.isFinite(numeric) ? currency.format(numeric) : 'R$ 0,00'
}

export function formatNumber(value: number): string {
  return integer.format(value)
}

export function formatDecimal(value: number): string {
  return decimal.format(value)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleDateString('pt-BR')
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('pt-BR')
}

export function pad(value: number): string {
  return String(value).padStart(2, '0')
}

/** Mesma formula combinatoria do back, para o aviso de custo antes da chamada. */
export function combinations(n: number, k: number): number {
  if (k > n || k < 0 || n < 0) return 0
  let result = 1
  for (let index = 1; index <= k; index += 1) {
    result = (result * (n - k + index)) / index
  }
  return Math.round(result)
}
