import { Link } from 'react-router-dom'

import { MODALITIES, MODALITY_LIST } from '@/config/modalities'
import { useBets, useBetsSummary, useGameBatches } from '@/shared/hooks/queries'
import { formatDate, formatDateTime, formatMoney, formatNumber } from '@/shared/lib/format'
import { Badge, EmptyState, Panel, StatCard } from '@/shared/ui/primitives'

export function DashboardPage() {
  const summary = useBetsSummary()
  const bets = useBets()
  const batches = useGameBatches(undefined, 8)

  const currentMonth = new Date().toISOString().slice(0, 7)
  const monthRows = (summary.data?.rows ?? []).filter((row) => row.month === currentMonth)
  const monthSpent = monthRows.reduce((total, row) => total + Number(row.spent), 0)
  const pending = (bets.data?.items ?? []).filter((bet) => bet.status === 'PENDING')
  const checked = (bets.data?.items ?? []).filter((bet) => bet.status === 'CHECKED')

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Gasto no mes" value={formatMoney(monthSpent)} hint={currentMonth} />
        <StatCard label="Total investido" value={formatMoney(summary.data?.total_spent ?? 0)} />
        <StatCard label="Total retornado" value={formatMoney(summary.data?.total_returned ?? 0)} />
        <StatCard
          label="Saldo"
          value={formatMoney(summary.data?.balance ?? 0)}
          tone={Number(summary.data?.balance ?? 0) >= 0 ? 'positive' : 'negative'}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {MODALITY_LIST.map((modality) => {
          const spent = (summary.data?.rows ?? [])
            .filter((row) => row.modality === modality.key)
            .reduce((total, row) => total + Number(row.spent), 0)

          return (
            <Link
              key={modality.key}
              to={`/m/${modality.slug}`}
              className="card group flex min-w-0 flex-col gap-1 p-5 transition hover:-translate-y-0.5 hover:border-ink-3 hover:shadow-md"
            >
              <span
                className="mb-2 block h-1.5 w-12 rounded-full transition-all group-hover:w-16"
                style={{ backgroundColor: modality.color }}
              />
              <p className="font-bold leading-tight text-ink-1">{modality.label}</p>
              <p className="text-xs leading-snug text-ink-3">
                {modality.boardKind === 'columns'
                  ? `${modality.columns} colunas de 0 a 9`
                  : `${modality.minPick} a ${modality.maxPick} de ${modality.universeMax}`}
              </p>
              <p className="mt-2 text-sm">
                <span className="text-ink-3">gasto </span>
                <span className="font-semibold text-ink-2">{formatMoney(spent)}</span>
              </p>
            </Link>
          )
        })}
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-2">
        <Panel
          title="Apostas pendentes"
          hint="Aguardando o concurso ser importado para a conferencia"
          actions={
            <Link to="/bets" className="btn-ghost px-3 py-1.5">
              Abrir conferencia
            </Link>
          }
          bodyClassName="max-h-[320px]"
          scroll
        >
          {pending.length ? (
            <ul className="divide-y divide-line-soft text-sm">
              {pending.map((bet) => (
                <li
                  key={bet.id}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Badge color={MODALITIES[bet.modality]?.color}>
                      {MODALITIES[bet.modality]?.label ?? bet.modality}
                    </Badge>
                    <span className="truncate text-ink-3">concurso {bet.contest_no}</span>
                  </span>
                  <span className="shrink-0 font-semibold text-ink-2">
                    {formatMoney(bet.cost)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Nenhuma aposta pendente" />
          )}
        </Panel>

        <Panel
          title="Ultimos lotes gerados"
          hint="Cada lote guarda a seed, entao pode ser reproduzido"
          bodyClassName="max-h-[320px]"
          scroll
        >
          {batches.data?.length ? (
            <ul className="divide-y divide-line-soft text-sm">
              {batches.data.map((batch) => (
                <li
                  key={batch.batch_id}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Badge color={MODALITIES[batch.modality]?.color}>
                      {MODALITIES[batch.modality]?.label ?? batch.modality}
                    </Badge>
                    <span className="truncate text-ink-3">
                      {formatNumber(batch.games_count)} jogos de {batch.numbers_per_game} numeros
                    </span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="block font-semibold text-ink-2">
                      {formatMoney(batch.total_cost)}
                    </span>
                    <span className="block text-xs text-ink-3">
                      {formatDateTime(batch.created_at)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="Nenhum lote gerado ainda"
              description="Escolha uma modalidade e use a aba Gerador."
            />
          )}
        </Panel>
      </div>

      <Panel title="Ultimas apostas conferidas" scroll>
        {checked.length ? (
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="table-head-sticky">
              <tr>
                <th className="px-1 pb-2 pt-0">Modalidade</th>
                <th className="px-1 pb-2 pt-0 text-right">Concurso</th>
                <th className="px-1 pb-2 pt-0">Data</th>
                <th className="px-1 pb-2 pt-0 text-right">Acertos</th>
                <th className="px-1 pb-2 pt-0 text-right">Custo</th>
              </tr>
            </thead>
            <tbody>
              {checked.slice(0, 10).map((bet) => (
                <tr key={bet.id} className="table-row">
                  <td className="px-1 py-2.5 text-ink-2">
                    {MODALITIES[bet.modality]?.label ?? bet.modality}
                  </td>
                  <td className="px-1 py-2.5 text-right text-ink-2">{bet.contest_no}</td>
                  <td className="whitespace-nowrap px-1 py-2.5 text-ink-3">
                    {formatDate(bet.placed_at)}
                  </td>
                  <td className="px-1 py-2.5 text-right font-semibold text-ink-1">
                    {bet.result?.hits ?? '-'}
                  </td>
                  <td className="px-1 py-2.5 text-right text-ink-2">{formatMoney(bet.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="Nenhuma aposta conferida ainda" />
        )}
      </Panel>
    </div>
  )
}
