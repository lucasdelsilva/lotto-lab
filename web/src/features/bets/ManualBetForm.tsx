import { useMemo, useState } from 'react'

import type { ModalityConfig } from '@/config/modalities'
import { MONTH_NAMES } from '@/config/modalities'
import { ApiError } from '@/shared/api/client'
import { useCreateBet, usePricingPreview } from '@/shared/hooks/queries'
import { formatMoney } from '@/shared/lib/format'
import { ColumnsBoard, NumbersBoard } from '@/shared/ui/Board'
import { Alert, Panel } from '@/shared/ui/primitives'

/**
 * Registro de aposta que ja foi paga na loteria. Nao passa pelo gerador: o usuario marca
 * as dezenas no volante ou cola os numeros, informa o concurso, e a aposta entra na
 * conferencia junto com as geradas pelo sistema.
 */
export function ManualBetForm({ config }: { config: ModalityConfig }) {
  const [selected, setSelected] = useState<number[]>([])
  const [columns, setColumns] = useState<number[][]>(() =>
    Array.from({ length: config.columns || 7 }, () => []),
  )
  const [contestNo, setContestNo] = useState('')
  const [month, setMonth] = useState('')
  const [costOverride, setCostOverride] = useState('')
  const [texto, setTexto] = useState('')

  const createBet = useCreateBet()
  const porColuna = config.boardKind === 'columns'

  const numeros = useMemo(
    () => (porColuna ? columns.flat() : selected),
    [porColuna, columns, selected],
  )
  const columnPicks = useMemo(
    () => (porColuna ? columns.map((coluna) => coluna.length) : undefined),
    [porColuna, columns],
  )

  const tamanhoValido = numeros.length >= config.minPick && numeros.length <= config.maxPick
  const colunasValidas =
    !porColuna || columns.every((coluna) => coluna.length >= 1 && coluna.length <= 3)

  const pricing = usePricingPreview(
    config.key,
    tamanhoValido ? numeros.length : config.minPick,
    1,
    colunasValidas ? columnPicks : undefined,
  )

  const precisaMes = config.extraField === 'month'
  const pronto =
    tamanhoValido &&
    colunasValidas &&
    contestNo.trim() !== '' &&
    (!precisaMes || month !== '') &&
    !createBet.isPending

  const erro = createBet.error instanceof ApiError ? createBet.error : null

  function alternar(valor: number) {
    setSelected((atual) =>
      atual.includes(valor)
        ? atual.filter((item) => item !== valor)
        : [...atual, valor].sort((a, b) => a - b),
    )
  }

  function alternarColuna(coluna: number, digito: number) {
    setColumns((atual) =>
      atual.map((valores, indice) => {
        if (indice !== coluna) return valores
        if (valores.includes(digito)) return valores.filter((item) => item !== digito)
        if (valores.length >= config.columnMaxPick) return valores
        return [...valores, digito].sort((a, b) => a - b)
      }),
    )
  }

  /** Aceita numeros colados em qualquer separador: espaco, virgula, ponto e virgula, quebra. */
  function aplicarTexto() {
    const valores = texto
      .split(/[^0-9]+/)
      .filter(Boolean)
      .map(Number)
    if (porColuna) {
      const proximo = Array.from({ length: config.columns }, (_, indice) =>
        valores[indice] === undefined ? [] : [valores[indice] as number],
      )
      setColumns(proximo)
    } else {
      const unicos = [...new Set(valores)]
        .filter((valor) => valor >= config.universeMin && valor <= config.universeMax)
        .sort((a, b) => a - b)
      setSelected(unicos)
    }
  }

  function limpar() {
    setSelected([])
    setColumns(Array.from({ length: config.columns || 7 }, () => []))
    setTexto('')
    setCostOverride('')
  }

  function salvar() {
    createBet.mutate(
      {
        modality: config.key,
        contest_no: Number(contestNo),
        numbers: numeros,
        ...(precisaMes || porColuna
          ? { extras: porColuna ? { columns } : { month: Number(month) } }
          : {}),
        ...(costOverride.trim() !== '' ? { cost: costOverride } : {}),
      },
      { onSuccess: () => limpar() },
    )
  }

  return (
    <Panel
      title="Registrar aposta ja feita"
      hint="Para os jogos que voce ja pagou na loteria. Eles entram na conferencia junto com os gerados aqui."
      bodyClassName="space-y-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-32">
          <label className="label mb-1.5" htmlFor="manual-contest">
            Concurso
          </label>
          <input
            id="manual-contest"
            type="number"
            min={1}
            placeholder="ex.: 3058"
            value={contestNo}
            onChange={(event) => setContestNo(event.target.value)}
            className="input"
          />
        </div>

        {precisaMes ? (
          <div className="w-40">
            <label className="label mb-1.5" htmlFor="manual-month">
              Mes da sorte
            </label>
            <select
              id="manual-month"
              className="input"
              value={month}
              onChange={(event) => setMonth(event.target.value)}
            >
              <option value="">escolha</option>
              {MONTH_NAMES.map((nome, indice) => (
                <option key={nome} value={indice + 1}>
                  {nome}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div className="w-36">
          <label className="label mb-1.5" htmlFor="manual-cost">
            Valor pago
          </label>
          <input
            id="manual-cost"
            type="number"
            min={0}
            step="0.01"
            placeholder={pricing.data ? pricing.data.per_game : 'automatico'}
            value={costOverride}
            onChange={(event) => setCostOverride(event.target.value)}
            className="input"
          />
        </div>

        <div className="min-w-[220px] flex-1">
          <label className="label mb-1.5" htmlFor="manual-text">
            Colar numeros
          </label>
          <div className="flex gap-2">
            <input
              id="manual-text"
              type="text"
              placeholder="05 14 18 28 32 47"
              value={texto}
              onChange={(event) => setTexto(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  aplicarTexto()
                }
              }}
              className="input"
            />
            <button type="button" className="btn-ghost shrink-0 px-3" onClick={aplicarTexto}>
              Aplicar
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <span className="label mb-0">
            {porColuna ? 'Marque um a tres digitos por coluna' : 'Marque as dezenas no volante'}
          </span>
          <span
            className={`text-sm font-semibold ${
              tamanhoValido && colunasValidas ? 'text-pos' : 'text-ink-3'
            }`}
          >
            {numeros.length} de {config.minPick} a {config.maxPick}
          </span>
        </div>

        <div className="flex justify-center overflow-x-auto">
          {porColuna ? (
            <ColumnsBoard config={config} selected={columns} onToggle={alternarColuna} size="sm" />
          ) : (
            <NumbersBoard config={config} selected={selected} onToggle={alternar} size="sm" />
          )}
        </div>
      </div>

      {erro ? (
        <Alert tone="danger" title={erro.problem?.title ?? 'Nao foi possivel registrar'}>
          {erro.message}
        </Alert>
      ) : null}

      {createBet.isSuccess ? (
        <Alert tone="success">Aposta registrada e ja aparece na lista abaixo.</Alert>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-2">
          Custo:{' '}
          <span className="font-semibold text-ink-1">
            {costOverride.trim() !== ''
              ? formatMoney(costOverride)
              : tamanhoValido && pricing.data
                ? formatMoney(pricing.data.per_game)
                : 'defina as dezenas'}
          </span>
          {costOverride.trim() === '' && tamanhoValido && pricing.data ? (
            <span className="ml-2 text-xs text-ink-3">calculado pela tabela oficial</span>
          ) : null}
        </p>

        <div className="flex gap-2">
          <button type="button" className="btn-ghost" onClick={limpar}>
            Limpar
          </button>
          <button type="button" className="btn-primary" onClick={salvar} disabled={!pronto}>
            {createBet.isPending ? 'Registrando' : 'Registrar aposta'}
          </button>
        </div>
      </div>
    </Panel>
  )
}
