import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { ModalityConfig } from '@/config/modalities'
import type { SuperSeteReport } from '@/shared/api/types'
import { formatDecimal, formatNumber } from '@/shared/lib/format'
import { EmptyState, Panel } from '@/shared/ui/primitives'

/**
 * Painel exclusivo do Super Sete. A estatistica e por coluna, entao a matriz 7 x 10
 * substitui todos os graficos por dezena das outras modalidades.
 */
export function SuperSetePanel({
  config,
  report,
}: {
  config: ModalityConfig
  report: SuperSeteReport
}) {
  const digits = Array.from({ length: 10 }, (_, index) => index)
  const maximum = Math.max(1, ...report.columns.frequency.flat())

  return (
    <div className="space-y-5">
      <Panel
        title="Matriz 7 x 10 de frequencia"
        hint="Cada celula traz a frequencia do digito naquela coluna e o z-score da janela. O tom acompanha o valor."
        scroll
      >
        <table className="w-full min-w-[560px] border-separate border-spacing-1">
          <thead>
            <tr>
              <th className="w-16 pb-1 text-left text-[11px] font-semibold uppercase tracking-wide text-ink-3">
                Coluna
              </th>
              {digits.map((digit) => (
                <th key={digit} className="pb-1 text-xs font-semibold text-ink-3">
                  {digit}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.columns.frequency.map((row, column) => (
              <tr key={column}>
                <th className="text-left text-xs font-bold text-ink-2">Coluna {column + 1}</th>
                {row.map((value, digit) => {
                  const z = report.columns.z_scores[column]?.[digit] ?? 0
                  const intensity = value / maximum
                  return (
                    <td key={digit}>
                      <div
                        className="flex h-11 flex-col items-center justify-center rounded-lg text-[11px] font-bold leading-tight"
                        style={{
                          backgroundColor: config.color,
                          opacity: 0.2 + intensity * 0.8,
                          color: 'var(--ink1)',
                        }}
                        title={`Coluna ${column + 1}, digito ${digit}: ${value} aparicoes, z ${formatDecimal(z)}`}
                      >
                        <span>{formatNumber(value)}</span>
                        <span className="text-[9px] font-medium opacity-70">
                          z {formatDecimal(z)}
                        </span>
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="grid items-start gap-5 xl:grid-cols-2">
        <Panel
          title="Soma dos sete digitos"
          hint={`P10 ${report.sum_distribution.p10}, mediana ${report.sum_distribution.p50}, P90 ${report.sum_distribution.p90}`}
        >
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={report.sum_distribution.histogram}
              margin={{ top: 4, right: 8, bottom: 0, left: -12 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
              <XAxis
                dataKey="value"
                tick={{ fontSize: 10, fill: 'var(--ink3)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--bd)' }}
                minTickGap={14}
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
                labelFormatter={(value) => `Soma ${value}`}
                formatter={(value: number) => [formatNumber(value), 'concursos']}
              />
              <Bar dataKey="count" fill={config.accent} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel
          title="Digitos repetidos"
          hint="Quantos digitos se repetem entre as colunas no mesmo concurso"
        >
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={report.repeated_digits}
              margin={{ top: 4, right: 8, bottom: 0, left: -12 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bd2)" vertical={false} />
              <XAxis
                dataKey="repeated"
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
                labelFormatter={(value) => `${value} digitos repetidos`}
                formatter={(value: number) => [formatNumber(value), 'concursos']}
              />
              <Bar dataKey="count" fill={config.color} radius={[3, 3, 0, 0]} maxBarSize={64} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel
        title="Resultados completos ja repetidos"
        hint="Os sete digitos exatamente iguais, na mesma ordem de colunas"
      >
        {report.repeated_results.length ? (
          <ul className="space-y-2 text-sm">
            {report.repeated_results.map((item) => (
              <li
                key={item.result.join('-')}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-line-soft pb-2 last:border-0"
              >
                <span className="font-mono text-base font-bold tracking-widest text-ink-2">
                  {item.result.join(' ')}
                </span>
                <span className="text-xs text-ink-3">
                  concursos {item.contests.join(', ')}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="Nenhum resultado completo se repetiu"
            description="Nos concursos importados, nenhuma combinacao das sete colunas saiu duas vezes."
          />
        )}
      </Panel>
    </div>
  )
}
