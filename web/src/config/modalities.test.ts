import { describe, expect, it } from 'vitest'

import { MODALITIES, MODALITY_KEYS, MODALITY_LIST, modalityFromSlug, universeOf } from './modalities'

describe('config de modalidades', () => {
  it('espelha os parametros oficiais do back', () => {
    expect(MODALITIES.MEGA_SENA).toMatchObject({
      universeMin: 1,
      universeMax: 60,
      minPick: 6,
      maxPick: 20,
      baseHits: 6,
      basePrice: 6,
    })
    expect(MODALITIES.LOTOFACIL).toMatchObject({ universeMax: 25, minPick: 15, basePrice: 3.5 })
    expect(MODALITIES.QUINA).toMatchObject({ universeMax: 80, minPick: 5, basePrice: 3 })
    expect(MODALITIES.DIA_DE_SORTE).toMatchObject({ universeMax: 31, minPick: 7, basePrice: 2.5 })
    expect(MODALITIES.SUPER_SETE).toMatchObject({ columns: 7, minPick: 7, maxPick: 21, basePrice: 3 })
  })

  it('so o Super Sete usa volante de colunas', () => {
    const columnBased = MODALITY_LIST.filter((item) => item.boardKind === 'columns')
    expect(columnBased.map((item) => item.key)).toEqual(['SUPER_SETE'])
  })

  it('o Dia de Sorte e o unico com campo extra', () => {
    const withExtra = MODALITY_LIST.filter((item) => item.extraField !== null)
    expect(withExtra.map((item) => item.key)).toEqual(['DIA_DE_SORTE'])
  })

  it('o volante comporta todo o universo', () => {
    for (const config of MODALITY_LIST) {
      if (config.boardKind !== 'numbers') continue
      const size = config.universeMax - config.universeMin + 1
      expect(config.boardRows * config.boardCols).toBeGreaterThanOrEqual(size)
    }
  })

  it('resolve a modalidade por slug e por chave', () => {
    expect(modalityFromSlug('mega-sena')?.key).toBe('MEGA_SENA')
    expect(modalityFromSlug('MEGA_SENA')?.key).toBe('MEGA_SENA')
    expect(modalityFromSlug('dia-de-sorte')?.key).toBe('DIA_DE_SORTE')
    expect(modalityFromSlug('inexistente')).toBeNull()
    expect(modalityFromSlug(undefined)).toBeNull()
  })

  it('gera o universo completo na ordem do volante', () => {
    expect(universeOf(MODALITIES.LOTOFACIL)).toHaveLength(25)
    expect(universeOf(MODALITIES.MEGA_SENA)[0]).toBe(1)
    expect(universeOf(MODALITIES.MEGA_SENA).at(-1)).toBe(60)
    expect(universeOf(MODALITIES.SUPER_SETE)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
  })

  it('todas as chaves tem config e slug unico', () => {
    const slugs = new Set(MODALITY_LIST.map((item) => item.slug))
    expect(slugs.size).toBe(MODALITY_KEYS.length)
    for (const key of MODALITY_KEYS) {
      expect(MODALITIES[key].key).toBe(key)
    }
  })
})
