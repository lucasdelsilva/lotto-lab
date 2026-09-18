import type { ModalityConfig } from '@/config/modalities'
import { MONTH_NAMES } from '@/config/modalities'
import { useBets, useCheckBets, useDeleteBet, useLatestDraw } from '@/shared/hooks/queries'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, Badge, EmptyState, Panel, Spinner } from '@/shared/ui/primitives'
import { ManualBetForm } from './ManualBetForm'

export function MyGamesTab({ config }: { config: ModalityConfig }) {
  const bets = useBets(config.key)
  const latest = useLatestDraw(config.key)
  const check = useCheckBets()
  const remover = useDeleteBet()

  const drawnNumbers = new Set(latest.data?.numbers ?? [])

  return (
    <div className="space-y-5">
      <Panel
        title={`Apostas de ${config.label}`}
        hint="A conferencia compara cada aposta com o concurso ja importado"
        actions={
          <button
            type="button"
            className="btn-primary"
            onClick={() => check.mutate(config.key)}
            disabled={check.isPending}
          >
            {check.isPending ? 'Conferindo' : 'Conferir pendentes'}
          </button>
        }
      >
        {check.data ? (
          <Alert tone={check.data.checked ? 'success' : 'info'}>
            {check.data.checked} aposta(s) conferida(s).
            {check.data.skipped
              ? ` ${check.data.skipped} ficaram pendentes porque o concurso ainda nao foi importado.`
              : ''}
          </Alert>
        ) : (
          <p className="text-sm leading-relaxed text-ink-3">
            Apostas com o concurso ja importado sao conferidas e recebem os acertos. As demais
            continuam pendentes ate voce importar a planilha atualizada.
          </p>
        )}
      </Panel>

      <ManualBetForm config={config} />

      {bets.isLoading ? <Spinner /> : null}

      {bets.data?.items.length ? (
        <ul className="space-y-3">
          {bets.data.items.map((bet) => (
            <li key={bet.id} className="card space-y-3 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2.5 text-sm">
                  <span className="font-semibold text-ink-2">Concurso {bet.contest_no}</span>
                  <span className="text-xs text-ink-3">{formatDate(bet.placed_at)}</span>
                  <Badge color={bet.status === 'CHECKED' ? 'var(--pos)' : 'var(--ink3)'}>
                    {bet.status === 'CHECKED' ? 'conferida' : 'pendente'}
                  </Badge>
                </div>
                <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
                  {bet.game_id === null ? <Badge color="var(--ink3)">manual</Badge> : null}
                  <span>
                    <span className="text-ink-3">custo </span>
                    <span className="font-semibold text-ink-2">{formatMoney(bet.cost)}</span>
                  </span>
                  {bet.result ? (
                    <span className="flex items-center gap-2">
                      <span className="text-ink-3">acertos </span>
                      <span className="text-lg font-bold text-ink-1">{bet.result.hits}</span>
                      {bet.result.extra_hit ? (
                        <Badge color={config.accent}>mes da sorte</Badge>
                      ) : null}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    title="Remover esta aposta"
                    className="text-xs font-semibold text-ink-3 transition hover:text-neg"
                    onClick={() => remover.mutate(bet.id)}
                    disabled={remover.isPending}
                  >
                    remover
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {Array.isArray(bet.extras.columns) ? (
                  <span className="font-mono text-base font-bold tracking-widest text-ink-2">
                    {(bet.extras.columns as number[][]).map((column) => column.join('')).join(' ')}
                  </span>
                ) : (
                  bet.numbers.map((value, index) => (
                    <NumberBall
                      key={`${value}-${index}`}
                      value={value}
                      tone={
                        bet.status === 'CHECKED' && drawnNumbers.has(value)
                          ? 'hit'
                          : bet.status === 'CHECKED'
                            ? 'default'
                            : 'selected'
                      }
                      color={config.color}
                      size="sm"
                    />
                  ))
                )}
                {typeof bet.extras.month === 'number' ? (
                  <Badge color={config.accent}>{MONTH_NAMES[(bet.extras.month as number) - 1]}</Badge>
                ) : null}
              </div>

              {bet.status === 'CHECKED' ? (
                <p className="text-xs text-ink-3">
                  Dezenas em verde sao as que sairam no ultimo concurso importado.
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : bets.isLoading ? null : (
        <EmptyState
          title="Nenhuma aposta registrada"
          description="Gere um lote na aba Gerador, informe o concurso e clique em Registrar."
        />
      )}
    </div>
  )
}
