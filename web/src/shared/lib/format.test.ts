import { describe, expect, it } from 'vitest'

import { combinations, formatDate, formatMoney, pad } from './format'

describe('formatacao', () => {
  it('formata moeda em real', () => {
    expect(formatMoney('42.00')).toMatch(/42,00/)
    expect(formatMoney(1260)).toMatch(/1\.260,00/)
    expect(formatMoney('nao numerico')).toBe('R$ 0,00')
  })

  it('formata data no padrao brasileiro', () => {
    expect(formatDate('2020-09-15')).toBe('15/09/2020')
    expect(formatDate(null)).toBe('-')
    expect(formatDate('data ruim')).toBe('-')
  })

  it('completa a dezena com zero a esquerda', () => {
    expect(pad(1)).toBe('01')
    expect(pad(60)).toBe('60')
  })
})

describe('combinatoria do preview', () => {
  it('bate com a formula usada no back', () => {
    expect(combinations(6, 6)).toBe(1)
    expect(combinations(7, 6)).toBe(7)
    expect(combinations(10, 6)).toBe(210)
    expect(combinations(20, 6)).toBe(38760)
    expect(combinations(16, 15)).toBe(16)
    expect(combinations(20, 15)).toBe(15504)
  })

  it('devolve zero quando k passa de n', () => {
    expect(combinations(3, 5)).toBe(0)
  })
})
