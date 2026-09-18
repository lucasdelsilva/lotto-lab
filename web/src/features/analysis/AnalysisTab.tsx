import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ModalityConfig } from '@/config/modalities'
import { MONTH_ABBR } from '@/config/modalities'
import { useAnalysis } from '@/shared/hooks/queries'
import { formatDecimal, formatNumber, pad } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, EmptyState, Field, Panel, Spinner, StatCard } from '@/shared/ui/primitives'
import { SuperSetePanel } from './SuperSetePanel'

type Metric = 'freq' | 'delay'

const METRIC_LABELS: Record<string, string> = {
  sum: 'Soma',
  even: 'Pares',
  primes: 'Primos',
  spread: 'Amplitude',
  max_consecutive: 'Consecutivos',
  multiples_of_3: 'Multiplos de 3',
  multiples_of_5: 'Multiplos de 5',
}

const HOT_COLOR = 'var(--hot-fg)'
const COLD_COLOR = 'var(--cold-fg)'
const MUTED_COLOR = 'var(--ink3)'

export function AnalysisTab({ config }: { config: ModalityConfig }) {
  const analysis = useAnalysis(config.key)
  const [metric, setMetric] = useState<Metric>('freq')

  const numbers = useMemo(() => analysis.data?.numbers ?? [], [analysis.data])
  const windowSize = analysis.data?.window ?? 50

  const chartData = useMemo(
    () =>
      numbers.map((row) => ({
        n: pad(row.n),
        freq: row.freq,
        delay: row.current_delay,
        temperature: row.temperature,
      })),
    [numbers],
  )

  const hot = numbers.filter((row) => row.temperature === 'hot')
  const cold = numbers.filter((row) => row.temperature === 'cold')
  const overdue = numbers.filter((row) => row.delay_ratio >= 1.5)

  if (analysis.isLoading) return <Spinner label="Calculando a analise" />

  if (analysis.isError) {
    return (
      <EmptyState
        title={`Sem historico de ${config.label}`}
        description="Importe a planilha oficial na aba Importar para liberar a analise."
      />
    )
  }

  if (!analysis.data) return null

  const meta = analysis.data.history_meta
  const ranges = analysis.data.patterns?.ranges
  const sequences = analysis.data.sequences
  const sumRange = ranges?.sum

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Concursos analisados"
          value={formatNumber(meta.total_draws)}
          accent={config.color}
        />
        <StatCard label="Faixa de concursos" value={`${meta.first_contest} a ${meta.last_contest}`} />
        <StatCard
          label="Janela de referencia"
          value={`${windowSize} concursos`}
          hint="Base do z-score e do componente de frequencia"
        />
        <StatCard
          label="Snapshot"
          value={analysis.data.cached ? 'em cache' : 'recalculado'}
          hint="O cache cai sozinho quando o historico muda"
        />
      </div>

      {config.boardKind === 'columns' && analysis.data.supersete ? (
        <SuperSetePanel config={config} report={analysis.data.supersete} />
      ) : null}

      {config.boardKind === 'numbers' ? (
        <>
          <Panel
            title={metric === 'freq' ? 'Frequencia por dezena' : 'Atraso atual por dezena'}
            hint="Z-score acima de 1,5 marca quente, abaixo de -1,5 marca fria"
            actions={
              <div className="inline-flex rounded-lg border border-line p-0.5">
                <button
                  type="button"
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                    metric === 'freq' ? 'bg-mod text-mod-on' : 'text-ink-3 hover:text-ink-1'
                  }`}
                  onClick={() => setMetric('freq')}
                >
                  Frequencia
                </button>
                <button
                  type="button"
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                    metric === 'delay' ? 'bg-mod text-mod-on' : 'text-ink-3 hover:text-ink-1'
                  }`}
                  onClick={() => setMetric('delay')}
                >
                  Atraso
                </button>
              </div>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
                <XAxis
                  dataKey="n"
                  tick={{ fontSize: 10, fill: 'var(--ink3)' }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--bd)' }}
                  interval={config.universeMax > 40 ? 2 : 0}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                />
                <Tooltip
                  cursor={{ fill: 'var(--s3)' }}
                  contentStyle={{
                    borderRadius: 8,
                    border: '1px solid var(--bd)',
                    background: 'var(--s1)',
                    color: 'var(--ink1)',
                    fontSize: 12,
                  }}
                  formatter={(value: number) => [
                    formatNumber(value),
                    metric === 'freq' ? 'aparicoes' : 'concursos de atraso',
                  ]}
                  labelFormatter={(label) => `Dezena ${label}`}
                />
                <Bar dataKey={metric} radius={[3, 3, 0, 0]} maxBarSize={26}>
                  {chartData.map((row) => (
                    <Cell
                      key={row.n}
                      fill={
                        row.temperature === 'hot'
                          ? HOT_COLOR
                          : row.temperature === 'cold'
                            ? COLD_COLOR
                            : config.color
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <div className="mt-5 grid gap-5 border-t border-line-soft pt-5 md:grid-cols-3">
              <TemperatureList title="Quentes" tone="hot" numbers={hot.map((row) => row.n)} />
              <TemperatureList title="Frias" tone="cold" numbers={cold.map((row) => row.n)} />
              <TemperatureList
                title="Atrasadas"
                tone="overdue"
                numbers={overdue.map((row) => row.n)}
                hint="Razao de atraso acima de 1,5"
              />
            </div>
          </Panel>

          <div className="grid items-start gap-5 xl:grid-cols-2">
            <Panel
              title="Distribuicao da soma"
              hint={
                sumRange
                  ? `Faixa tipica de ${formatDecimal(sumRange.p10)} a ${formatDecimal(sumRange.p90)}, mediana ${formatDecimal(sumRange.p50)}`
                  : undefined
              }
            >
              {analysis.data.patterns?.sum_histogram.length ? (
                <>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart
                      data={analysis.data.patterns.sum_histogram}
                      margin={{ top: 4, right: 8, bottom: 0, left: -12 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
                      <XAxis
                        dataKey="start"
                        tick={{ fontSize: 10, fill: 'var(--ink3)' }}
                        tickLine={false}
                        axisLine={{ stroke: 'var(--bd)' }}
                        interval="preserveStartEnd"
                        minTickGap={18}
                        tickFormatter={(value: number) => String(Math.round(value))}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                        tickLine={false}
                        axisLine={false}
                        width={48}
                      />
                      <Tooltip
                        cursor={{ fill: 'var(--s3)' }}
                        contentStyle={{
                    borderRadius: 8,
                    border: '1px solid var(--bd)',
                    background: 'var(--s1)',
                    color: 'var(--ink1)',
                    fontSize: 12,
                  }}
                        labelFormatter={(value) => `Soma a partir de ${Math.round(Number(value))}`}
                        formatter={(value: number) => [formatNumber(value), 'concursos']}
                      />
                      <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                        {analysis.data.patterns.sum_histogram.map((bin) => {
                          // Barra dentro de P10 a P90 recebe a cor da modalidade; fora dela
                          // fica apagada, o que mostra a faixa sem precisar de linha guia.
                          const inside =
                            !sumRange || (bin.end >= sumRange.p10 && bin.start <= sumRange.p90)
                          return (
                            <Cell
                              key={bin.start}
                              fill={inside ? config.color : MUTED_COLOR}
                            />
                          )
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  {sumRange ? (
                    <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-line-soft pt-3 text-xs text-ink-3">
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="h-2.5 w-2.5 rounded-sm"
                          style={{ backgroundColor: config.color }}
                        />
                        dentro de P10 a P90
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="h-2.5 w-2.5 rounded-sm"
                          style={{ backgroundColor: MUTED_COLOR }}
                        />
                        fora da faixa
                      </span>
                      <span>
                        P10 {formatDecimal(sumRange.p10)} | P50 {formatDecimal(sumRange.p50)} | P90{' '}
                        {formatDecimal(sumRange.p90)}
                      </span>
                    </div>
                  ) : null}
                </>
              ) : null}
            </Panel>

            <Panel title="Pares e impares" hint="Quantidade de dezenas pares por concurso">
              {analysis.data.patterns?.even_distribution.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={analysis.data.patterns.even_distribution}
                    margin={{ top: 4, right: 8, bottom: 0, left: -12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
                    <XAxis
                      dataKey="even"
                      tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                      tickLine={false}
                      axisLine={{ stroke: 'var(--bd)' }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                      tickLine={false}
                      axisLine={false}
                      width={48}
                    />
                    <Tooltip
                      cursor={{ fill: 'var(--s3)' }}
                      contentStyle={{
                    borderRadius: 8,
                    border: '1px solid var(--bd)',
                    background: 'var(--s1)',
                    color: 'var(--ink1)',
                    fontSize: 12,
                  }}
                      labelFormatter={(value) => `${value} pares`}
                      formatter={(value: number) => [formatNumber(value), 'concursos']}
                    />
                    <Bar dataKey="count" fill={config.accent} radius={[3, 3, 0, 0]} maxBarSize={64} />
                  </BarChart>
                </ResponsiveContainer>
              ) : null}
            </Panel>
          </div>

          <Panel
            title="Mapa de atraso"
            hint="Cada linha e uma dezena, cada coluna um dos ultimos 60 concursos. Quanto mais escuro, maior o atraso naquele momento."
          >
            <DelayHeatmap config={config} matrix={analysis.data.delay_heatmap ?? []} />
          </Panel>

          <div className="grid items-start gap-5 xl:grid-cols-2">
            <Panel
              title="Pares com maior lift"
              hint="Lift acima de 1 indica par que saiu junto mais do que o acaso sugeriria"
            >
              <table className="w-full text-left text-sm">
                <thead className="table-head-sticky static">
                  <tr>
                    <th className="px-1 pb-2 pt-0">Par</th>
                    <th className="px-1 pb-2 pt-0 text-right">Juntos</th>
                    <th className="px-1 pb-2 pt-0 text-right">Lift</th>
                  </tr>
                </thead>
                <tbody>
                  {(analysis.data.pairs?.top_pairs ?? []).map((pair) => (
                    <tr key={pair.pair.join('-')} className="table-row">
                      <td className="px-1 py-2">
                        <span className="flex gap-1">
                          <NumberBall value={pair.pair[0]} size="sm" />
                          <NumberBall value={pair.pair[1]} size="sm" />
                        </span>
                      </td>
                      <td className="px-1 py-2 text-right text-ink-2">
                        {formatNumber(pair.count)}
                      </td>
                      <td className="px-1 py-2 text-right font-semibold text-ink-2">
                        {formatDecimal(pair.lift)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>

            <Panel
              title="Faixas por metrica"
              hint="Faixas historicas usadas pelos filtros do gerador"
            >
              {ranges ? (
                <table className="w-full text-left text-sm">
                  <thead className="table-head-sticky static">
                    <tr>
                      <th className="px-1 pb-2 pt-0">Metrica</th>
                      <th className="px-1 pb-2 pt-0 text-right">P10</th>
                      <th className="px-1 pb-2 pt-0 text-right">P50</th>
                      <th className="px-1 pb-2 pt-0 text-right">P90</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(ranges).map(([name, range]) => (
                      <tr key={name} className="table-row">
                        <td className="px-1 py-2 font-medium text-ink-2">
                          {METRIC_LABELS[name] ?? name}
                        </td>
                        <td className="px-1 py-2 text-right text-ink-2">
                          {formatDecimal(range.p10)}
                        </td>
                        <td className="px-1 py-2 text-right font-semibold text-ink-2">
                          {formatDecimal(range.p50)}
                        </td>
                        <td className="px-1 py-2 text-right text-ink-2">
                          {formatDecimal(range.p90)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </Panel>
          </div>

          <Panel title="Sequencias e repeticao" hint="Distribuicoes observadas no historico">
            {sequences ? (
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                <Field label="Maior sequencia de consecutivos">
                  media de {formatDecimal(sequences.max_consecutive.mean)}, P90 em{' '}
                  {sequences.max_consecutive.p90}
                </Field>
                <Field label="Repeticao do concurso anterior">
                  faixa comum de {sequences.repeat_from_previous.p10} a{' '}
                  {sequences.repeat_from_previous.p90}, mediana {sequences.repeat_from_previous.p50}
                </Field>
                <Field label="Pares que nunca sairam juntos">
                  {formatNumber(analysis.data.pairs?.never_together.length ?? 0)} combinacoes
                </Field>
                <Field label="Ultimo concurso">
                  <div className="mt-1 flex flex-wrap gap-1">
                    {sequences.last_draw.map((value, index) => (
                      <NumberBall key={`${value}-${index}`} value={value} size="sm" />
                    ))}
                  </div>
                </Field>
              </div>
            ) : null}
          </Panel>
        </>
      ) : null}

      {config.extraField === 'month' && analysis.data.months?.length ? (
        <Panel title="Mes da sorte" hint="Em todo concurso um mes e sorteado">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={analysis.data.months.map((row) => ({
                ...row,
                label: MONTH_ABBR[row.month - 1] ?? String(row.month),
              }))}
              margin={{ top: 4, right: 8, bottom: 0, left: -12 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--bd)' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                tickLine={false}
                axisLine={false}
                width={48}
              />
              <Tooltip
                cursor={{ fill: 'var(--s3)' }}
                contentStyle={{
                    borderRadius: 8,
                    border: '1px solid var(--bd)',
                    background: 'var(--s1)',
                    color: 'var(--ink1)',
                    fontSize: 12,
                  }}
                formatter={(value: number) => [formatNumber(value), 'sorteios']}
              />
              <Bar dataKey="count" fill={config.color} radius={[3, 3, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      ) : null}

      <Alert tone="info">
        Estes numeros descrevem o historico observado. Sorteio e aleatorio: nenhuma estatistica aqui
        muda a probabilidade do proximo concurso.
      </Alert>
    </div>
  )
}

function TemperatureList({
  title,
  tone,
  numbers,
  hint,
}: {
  title: string
  tone: 'hot' | 'cold' | 'overdue'
  numbers: number[]
  hint?: string
}) {
  return (
    <div className="min-w-0">
      <p className="label mb-1.5">
        {title}
        <span className="ml-1 font-normal normal-case tracking-normal text-ink-3">
          ({numbers.length})
        </span>
      </p>
      {numbers.length ? (
        <div className="flex flex-wrap gap-1">
          {numbers.map((value) => (
            <NumberBall key={value} value={value} tone={tone} size="sm" />
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-3">nenhuma no momento</p>
      )}
      {hint ? <p className="mt-1.5 text-xs text-ink-3">{hint}</p> : null}
    </div>
  )
}

function DelayHeatmap({ config, matrix }: { config: ModalityConfig; matrix: number[][] }) {
  if (!matrix.length) return <p className="text-sm text-ink-3">Sem dados suficientes.</p>

  const maximum = Math.max(1, ...matrix.flat())
  const columns = matrix[0]?.length ?? 0

  return (
    <div>
      {/*
       * table-fixed + w-full faz as colunas dividirem a largura disponivel, em vez de
       * ficarem nos 12px fixos que deixavam metade do card vazia. A altura nao e limitada:
       * quem rola e a pagina, nao o card.
       */}
      <div className="overflow-x-auto rounded-lg border border-line-soft">
        <table className="w-full min-w-[560px] table-fixed border-separate border-spacing-0">
          <tbody>
            {matrix.map((row, index) => (
              <tr key={index}>
                {/* A coluna da dezena fica fixa para a leitura nao se perder no scroll. */}
                <th className="sticky left-0 z-10 w-9 bg-surface-1 px-2 py-[1px] text-right text-[10px] font-semibold text-ink-3">
                  {pad(config.universeMin + index)}
                </th>
                {row.map((value, column) => (
                  <td key={column} className="p-[1px]">
                    <span
                      title={`Dezena ${config.universeMin + index}, atraso de ${value} concurso(s)`}
                      className="block h-3.5 w-full rounded-[2px]"
                      style={{
                        backgroundColor: config.color,
                        opacity: 0.1 + (value / maximum) * 0.9,
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-3">
        <span>
          {matrix.length} dezenas x {columns} concursos, do mais antigo a esquerda ao mais recente a
          direita
        </span>
        <span className="inline-flex items-center gap-2">
          sem atraso
          <span className="flex">
            {[0.1, 0.3, 0.5, 0.7, 0.9].map((opacity) => (
              <span
                key={opacity}
                className="h-3 w-5"
                style={{ backgroundColor: config.color, opacity }}
              />
            ))}
          </span>
          atraso maximo
        </span>
      </div>
    </div>
  )
}
