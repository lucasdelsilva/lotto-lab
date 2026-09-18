import { useEffect } from 'react'

import type { ModalityConfig } from '@/config/modalities'
import { useAIReview, useGameInsight } from '@/shared/hooks/queries'
import { formatDecimal, formatNumber } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, Spinner } from '@/shared/ui/primitives'

const METRIC_LABELS: Record<string, string> = {
  sum: 'Soma',
  even: 'Pares',
  primes: 'Primos',
  spread: 'Amplitude',
  max_consecutive: 'Consecutivos',
  multiples_of_3: 'Multiplos de 3',
  multiples_of_5: 'Multiplos de 5',
}

type InsightMetrics = {
  sum: number
  even: number
  primes: number
  spread: number
  max_consecutive: number
  multiples_of_3: number
  multiples_of_5: number
}

const METRIC_TO_VALUE: Record<string, keyof InsightMetrics> = {
  sum: 'sum',
  even: 'even',
  primes: 'primes',
  spread: 'spread',
  max_consecutive: 'max_consecutive',
  multiples_of_3: 'multiples_of_3',
  multiples_of_5: 'multiples_of_5',
}

/**
 * Painel lateral que so e montado quando o usuario abre o jogo. O detalhamento nunca vem
 * na resposta da geracao, entao e aqui que a chamada de insight acontece.
 */
export function InsightPanel({
  config,
  gameId,
  onClose,
}: {
  config: ModalityConfig
  gameId: string
  onClose: () => void
}) {
  const insight = useGameInsight(gameId)
  const review = useAIReview()

  // Fechar com Esc e travar o scroll do fundo enquanto o painel estiver aberto.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-[rgba(10,14,18,0.44)] backdrop-blur-[2px]"
      onClick={onClose}
    >
      <aside
        className="flex h-full w-full max-w-xl flex-col bg-surface-1 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div>
            <h3 className="text-xl font-bold leading-tight text-ink-1">Detalhe do jogo</h3>
            <p className="mt-0.5 text-sm text-ink-3">{config.label}</p>
          </div>
          <button type="button" className="btn-ghost px-3 py-1.5" onClick={onClose}>
            Fechar
          </button>
        </header>

        <div className="scroll-area flex-1 px-6 py-5">
          {insight.isLoading ? <Spinner label="Carregando o detalhamento" /> : null}
          {insight.isError ? (
            <Alert tone="danger">Nao foi possivel carregar o detalhamento.</Alert>
          ) : null}

          {insight.data ? (
            <div className="space-y-6">
              <div className="flex flex-wrap gap-1.5">
                {insight.data.numbers.map((value, index) => (
                  <NumberBall
                    key={`${value}-${index}`}
                    value={value}
                    tone="selected"
                    color={config.color}
                    padded={config.boardKind !== 'columns'}
                  />
                ))}
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Metric label="Score do motor" value={formatDecimal(insight.data.engine_score)} />
                <Metric label="Aderencia historica" value={formatDecimal(insight.data.fit_score)} />
                <Metric
                  label="Ja sorteado"
                  value={insight.data.already_drawn ? 'sim' : 'nao'}
                  tone={insight.data.already_drawn ? 'danger' : 'ok'}
                />
              </div>

              {insight.data.already_drawn ? (
                <Alert tone="warning" title="Essa combinacao ja apareceu no historico">
                  Concursos: {insight.data.matched_contests.join(', ') || 'nao identificados'}
                </Alert>
              ) : null}

              <section>
                <p className="label mb-1.5">Melhor correspondencia historica</p>
                <p className="text-sm leading-relaxed text-ink-2">
                  {insight.data.best_historical_match.contest
                    ? `Esse jogo teria feito ${insight.data.best_historical_match.hits} pontos no concurso ${insight.data.best_historical_match.contest}.`
                    : 'Sem correspondencia no historico importado.'}
                </p>
              </section>

              {config.boardKind === 'numbers' ? (
                <section>
                  <p className="label mb-1.5">Metricas contra a faixa historica</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs font-semibold uppercase tracking-wide text-ink-3">
                      <tr>
                        <th className="pb-2">Metrica</th>
                        <th className="pb-2 text-right">Jogo</th>
                        <th className="pb-2 text-right">P10</th>
                        <th className="pb-2 text-right">P90</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(METRIC_LABELS).map(([key, label]) => {
                        const range = insight.data.pattern_ranges[key]
                        const valueKey = METRIC_TO_VALUE[key]
                        const value = valueKey
                          ? (insight.data.metrics as unknown as InsightMetrics)[valueKey]
                          : undefined
                        const inside =
                          range && value !== undefined
                            ? value >= range.p10 && value <= range.p90
                            : true
                        return (
                          <tr key={key} className="table-row">
                            <td className="py-2 text-ink-2">{label}</td>
                            <td
                              className={`py-2 text-right font-semibold ${
                                inside ? 'text-pos' : 'text-[var(--late-fg)]'
                              }`}
                            >
                              {value !== undefined ? formatNumber(value) : '-'}
                            </td>
                            <td className="py-2 text-right text-ink-3">
                              {range ? formatDecimal(range.p10) : '-'}
                            </td>
                            <td className="py-2 text-right text-ink-3">
                              {range ? formatDecimal(range.p90) : '-'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  <p className="mt-2 text-xs text-ink-3">
                    Verde indica metrica dentro da faixa tipica do historico.
                  </p>
                </section>
              ) : null}

              <section className="grid gap-4 sm:grid-cols-3">
                <NumbersGroup
                  title="Quentes usadas"
                  numbers={insight.data.hot_numbers_used}
                  tone="hot"
                />
                <NumbersGroup
                  title="Frias usadas"
                  numbers={insight.data.cold_numbers_used}
                  tone="cold"
                />
                <NumbersGroup
                  title="Atrasadas usadas"
                  numbers={insight.data.overdue_numbers_used}
                  tone="overdue"
                />
              </section>

              {config.boardKind === 'numbers' ? (
                <section>
                  <p className="label mb-1.5">Distribuicao por quadrante</p>
                  <div className="grid grid-cols-4 gap-2">
                    {insight.data.metrics.quadrants.map((count, index) => (
                      <div
                        key={index}
                        className="rounded-lg border border-line py-2.5 text-center"
                      >
                        <span className="block text-xs text-ink-3">Q{index + 1}</span>
                        <span className="text-lg font-bold text-ink-2">{count}</span>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              <section className="border-t border-line pt-5">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => review.mutate(insight.data.batch_id)}
                  disabled={review.isPending}
                >
                  {review.isPending ? 'Consultando a IA' : 'Pedir leitura da IA para o lote'}
                </button>

                {review.data && !review.data.ai_available ? (
                  <div className="mt-3">
                    <Alert tone="info">
                      {review.data.error ??
                        'A camada de IA esta desligada. A analise deterministica continua completa.'}
                    </Alert>
                  </div>
                ) : null}

                {review.data?.analysis ? (
                  <div className="mt-4 space-y-3 text-sm">
                    <p className="leading-relaxed text-ink-2">
                      {review.data.analysis.overview}
                    </p>
                    <ul className="space-y-2">
                      {review.data.analysis.ranked_games.map((ranked) => (
                        <li key={ranked.id} className="rounded-lg border border-line p-3">
                          <p className="font-semibold text-ink-2">
                            {ranked.rank}. aderencia {formatDecimal(ranked.statistical_fit)}
                          </p>
                          <p className="mt-1 leading-relaxed text-ink-2">{ranked.rationale}</p>
                        </li>
                      ))}
                    </ul>
                    <p className="text-xs leading-relaxed text-ink-3">
                      {review.data.analysis.disclaimer}
                    </p>
                  </div>
                ) : null}
              </section>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'danger' }) {
  return (
    <div className="rounded-lg border border-line p-3">
      <p className="text-xs uppercase tracking-wide text-ink-3">{label}</p>
      <p
        className={`mt-0.5 text-lg font-bold leading-tight ${
          tone === 'danger' ? 'text-neg' : tone === 'ok' ? 'text-pos' : 'text-ink-1'
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function NumbersGroup({
  title,
  numbers,
  tone,
}: {
  title: string
  numbers: number[]
  tone: 'hot' | 'cold' | 'overdue'
}) {
  return (
    <div className="min-w-0">
      <p className="label mb-1.5">{title}</p>
      {numbers.length ? (
        <div className="flex flex-wrap gap-1">
          {numbers.map((value) => (
            <NumberBall key={value} value={value} tone={tone} size="sm" />
          ))}
        </div>
      ) : (
        <p className="text-xs text-ink-3">nenhuma</p>
      )}
    </div>
  )
}
