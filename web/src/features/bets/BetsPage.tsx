import { useState } from 'react'

import { MODALITIES, MODALITY_LIST, type ModalityKey } from '@/config/modalities'
import { useBets, useBetsSummary, useCheckBets } from '@/shared/hooks/queries'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, Badge, EmptyState, Panel, Spinner, StatCard } from '@/shared/ui/primitives'

export function BetsPage() {
  const [modality, setModality] = useState<ModalityKey | ''>('')
  const [status, setStatus] = useState<string>('')

  const summary = useBetsSummary()
  const bets = useBets(modality === '' ? undefined : modality)
  const check = useCheckBets()

  const filtered = (bets.data?.items ?? []).filter((bet) => (status ? bet.status === status : true))

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total apostado" value={formatMoney(summary.data?.total_spent ?? 0)} />
        <StatCard
          label="Total premiado"
          value={formatMoney(summary.data?.total_returned ?? 0)}
          hint="Depende da planilha trazer a faixa de premiacao"
        />
        <StatCard
          label="Saldo"
          value={formatMoney(summary.data?.balance ?? 0)}
          tone={Number(summary.data?.balance ?? 0) >= 0 ? 'positive' : 'negative'}
        />
      </div>

      <Panel title="Filtros" hint="Combine modalidade e situacao para recortar a lista">
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[180px]">
            <label className="label mb-1.5" htmlFor="modality">
              Modalidade
            </label>
            <select
              id="modality"
              className="input"
              value={modality}
              onChange={(event) => setModality(event.target.value as ModalityKey | '')}
            >
              <option value="">Todas</option>
              {MODALITY_LIST.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div className="min-w-[160px]">
            <label className="label mb-1.5" htmlFor="status">
              Situacao
            </label>
            <select
              id="status"
              className="input"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="">Todas</option>
              <option value="PENDING">Pendentes</option>
              <option value="CHECKED">Conferidas</option>
            </select>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={() => check.mutate(modality === '' ? undefined : modality)}
            disabled={check.isPending}
          >
            {check.isPending ? 'Conferindo' : 'Conferir pendentes'}
          </button>
        </div>

        {check.data ? (
          <div className="mt-4">
            <Alert tone={check.data.checked ? 'success' : 'info'}>
              {check.data.checked} aposta(s) conferida(s), {check.data.skipped} sem concurso
              importado.
            </Alert>
          </div>
        ) : null}
      </Panel>

      <Panel title="Gasto por modalidade e mes" scroll>
        {summary.data?.rows.length ? (
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="table-head-sticky">
              <tr>
                <th className="px-1 pb-2 pt-0">Mes</th>
                <th className="px-1 pb-2 pt-0">Modalidade</th>
                <th className="px-1 pb-2 pt-0 text-right">Apostas</th>
                <th className="px-1 pb-2 pt-0 text-right">Gasto</th>
                <th className="px-1 pb-2 pt-0 text-right">Premio</th>
                <th className="px-1 pb-2 pt-0 text-right">Saldo</th>
              </tr>
            </thead>
            <tbody>
              {summary.data.rows.map((row) => (
                <tr key={`${row.month}-${row.modality}`} className="table-row">
                  <td className="whitespace-nowrap px-1 py-2.5 text-ink-2">{row.month}</td>
                  <td className="px-1 py-2.5">
                    <Badge color={MODALITIES[row.modality]?.color}>
                      {MODALITIES[row.modality]?.label ?? row.modality}
                    </Badge>
                  </td>
                  <td className="px-1 py-2.5 text-right text-ink-2">{row.bets}</td>
                  <td className="px-1 py-2.5 text-right text-ink-2">{formatMoney(row.spent)}</td>
                  <td className="px-1 py-2.5 text-right text-ink-2">
                    {formatMoney(row.returned)}
                  </td>
                  <td
                    className={`px-1 py-2.5 text-right font-semibold ${
                      Number(row.balance) >= 0 ? 'text-pos' : 'text-neg'
                    }`}
                  >
                    {formatMoney(row.balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="Nenhuma aposta registrada ainda" />
        )}
      </Panel>

      <Panel
        title="Apostas"
        hint={`${filtered.length} de ${bets.data?.total ?? 0} registradas`}
        bodyClassName="max-h-[520px]"
        scroll
      >
        {bets.isLoading ? <Spinner /> : null}
        {filtered.length ? (
          <ul className="divide-y divide-line-soft">
            {filtered.map((bet) => {
              const config = MODALITIES[bet.modality]
              return (
                <li
                  key={bet.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Badge color={config?.color}>{config?.label ?? bet.modality}</Badge>
                    <span className="text-xs text-ink-3">concurso {bet.contest_no}</span>
                    <span className="text-xs text-ink-3">{formatDate(bet.placed_at)}</span>
                    {Array.isArray(bet.extras.columns) ? (
                      <span className="font-mono text-sm font-bold tracking-widest text-ink-2">
                        {(bet.extras.columns as number[][])
                          .map((column) => column.join(''))
                          .join(' ')}
                      </span>
                    ) : (
                      bet.numbers.map((value, index) => (
                        <NumberBall key={`${value}-${index}`} value={value} size="sm" />
                      ))
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-x-5 text-sm">
                    <span>
                      <span className="text-ink-3">custo </span>
                      <span className="font-semibold text-ink-2">{formatMoney(bet.cost)}</span>
                    </span>
                    {bet.result ? (
                      <span>
                        <span className="text-ink-3">acertos </span>
                        <span className="font-bold text-ink-1">{bet.result.hits}</span>
                      </span>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ul>
        ) : bets.isLoading ? null : (
          <EmptyState title="Nenhuma aposta para os filtros escolhidos" />
        )}
      </Panel>
    </div>
  )
}
