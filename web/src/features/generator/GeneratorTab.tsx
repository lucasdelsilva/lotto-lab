import { useState } from 'react'

import type { ModalityConfig } from '@/config/modalities'
import { MONTH_NAMES } from '@/config/modalities'
import { ApiError } from '@/shared/api/client'
import type { FilterId, GeneratorProfile } from '@/shared/api/types'
import {
  useCreateBet,
  useFilterCatalog,
  useGenerator,
  usePricingPreview,
} from '@/shared/hooks/queries'
import { formatMoney, formatNumber } from '@/shared/lib/format'
import { ColumnsBoard } from '@/shared/ui/Board'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, Badge, EmptyState, Panel } from '@/shared/ui/primitives'
import { FiltersPanel } from './FiltersPanel'
import { InsightPanel } from './InsightPanel'

const PROFILES: { id: GeneratorProfile; label: string; description: string }[] = [
  { id: 'balanced', label: 'Equilibrado', description: 'Frequencia e atraso com o mesmo peso' },
  { id: 'hot', label: 'Quentes', description: 'Privilegia dezenas com z-score alto na janela' },
  { id: 'cold', label: 'Frias', description: 'Privilegia dezenas atrasadas' },
  { id: 'pattern', label: 'Padroes', description: 'Peso maior na co-ocorrencia entre dezenas' },
  { id: 'uniform', label: 'Uniforme', description: 'Sorteio uniforme, grupo de controle' },
]

export function GeneratorTab({ config }: { config: ModalityConfig }) {
  const [numbersPerGame, setNumbersPerGame] = useState(config.minPick)
  const [games, setGames] = useState(5)
  const [profile, setProfile] = useState<GeneratorProfile>('balanced')
  const [seed, setSeed] = useState<string>('')
  const [budget, setBudget] = useState<string>('')
  // Undefined significa: todos os filtros da modalidade ligados, que e o padrao do back.
  const [disabled, setDisabled] = useState<Set<FilterId>>(() => new Set())
  const [rejectDrawn, setRejectDrawn] = useState(true)
  const [openGameId, setOpenGameId] = useState<string | null>(null)
  const [contestNo, setContestNo] = useState<string>('')
  // Quais jogos deste lote ja viraram aposta. Some junto com o lote.
  const [registered, setRegistered] = useState<Set<string>>(() => new Set())

  const catalog = useFilterCatalog(config.key)
  const todosOsFiltros = (catalog.data?.filters ?? []).map((item) => item.id)
  const ligados = new Set(todosOsFiltros.filter((id) => !disabled.has(id)))

  const pricing = usePricingPreview(config.key, numbersPerGame, games)
  const generator = useGenerator(config.key)
  const createBet = useCreateBet()

  const error = generator.error instanceof ApiError ? generator.error : null
  const budgetValue = budget.trim() === '' ? null : Number(budget)
  const total = pricing.data ? Number(pricing.data.total) : 0
  const overBudget = budgetValue !== null && total > budgetValue

  function submit() {
    // O lote novo nao herda o registro do anterior: o aviso de aposta registrada ficava
    // na tela enquanto o usuario so gerava jogos.
    setRegistered(new Set())
    createBet.reset()
    generator.mutate({
      numbers_per_game: numbersPerGame,
      games,
      profile,
      seed: seed.trim() === '' ? null : Number(seed),
      budget_limit: budgetValue,
      filters: {
        enabled: [...ligados],
        max_consecutive: null,
        min_quadrants_covered: 0,
        on_already_drawn: rejectDrawn ? 'reject' : 'flag',
      },
      extras: config.extraField === 'month' ? { month_strategy: 'auto' } : undefined,
    })
  }

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
      <Panel
        title="Parametros"
        hint="O custo e recalculado a cada mudanca"
        className="xl:sticky xl:top-6"
        bodyClassName="space-y-5"
      >
        <div>
          <label className="label mb-1.5" htmlFor="numbers">
            Quantidade de numeros
          </label>
          <input
            id="numbers"
            type="range"
            min={config.minPick}
            max={config.maxPick}
            value={numbersPerGame}
            onChange={(event) => setNumbersPerGame(Number(event.target.value))}
            className="w-full accent-caixa-blue"
          />
          <div className="mt-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="font-bold text-ink-1">{numbersPerGame} numeros</span>
            <span className="text-right text-xs text-ink-3">
              {pricing.data
                ? `${formatNumber(pricing.data.combinations)} jogos simples`
                : 'calculando'}
            </span>
          </div>
          <div className="mt-0.5 flex justify-between text-[11px] text-ink-3">
            <span>min {config.minPick}</span>
            <span>max {config.maxPick}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label mb-1.5" htmlFor="games">
              Jogos
            </label>
            <input
              id="games"
              type="number"
              min={1}
              max={200}
              value={games}
              onChange={(event) => setGames(Math.max(1, Number(event.target.value)))}
              className="input"
            />
          </div>
          <div>
            <label className="label mb-1.5" htmlFor="seed">
              Seed
            </label>
            <input
              id="seed"
              type="number"
              min={0}
              placeholder="aleatoria"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              className="input"
            />
          </div>
        </div>

        <div>
          <span className="label mb-1.5">Perfil</span>
          <div className="space-y-1.5">
            {PROFILES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setProfile(item.id)}
                className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
                  profile === item.id
                    ? 'border-mod bg-[color-mix(in_oklab,var(--mod)_10%,transparent)] ring-1 ring-[color-mix(in_oklab,var(--mod)_25%,transparent)]'
                    : 'border-line hover:bg-surface-2'
                }`}
              >
                <span className="block text-sm font-semibold text-ink-1">{item.label}</span>
                <span className="mt-0.5 block text-xs leading-snug text-ink-3">
                  {item.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label mb-1.5" htmlFor="budget">
            Orcamento maximo do lote
          </label>
          <input
            id="budget"
            type="number"
            min={0}
            step="0.01"
            placeholder="sem limite"
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            className="input"
          />
        </div>

        <FiltersPanel
          config={config}
          enabled={ligados}
          onToggle={(id) =>
            setDisabled((atual) => {
              const proximo = new Set(atual)
              if (proximo.has(id)) proximo.delete(id)
              else proximo.add(id)
              return proximo
            })
          }
          onToggleAll={(ids, valor) => setDisabled(valor ? new Set() : new Set(ids))}
        />

        <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-line bg-surface-2 px-3 py-2.5 text-sm leading-snug text-ink-2">
          <input
            type="checkbox"
            checked={rejectDrawn}
            onChange={(event) => setRejectDrawn(event.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-caixa-blue"
          />
          <span>
            <span className="block font-medium text-ink-1">
              Nunca repetir combinacao ja sorteada
            </span>
            <span className="text-xs text-ink-3">
              O jogo cuja combinacao ja saiu em algum concurso e descartado e refeito, nao
              chega a aparecer na lista.
            </span>
          </span>
        </label>

        <div className="rounded-lg border border-line bg-surface-2 p-4">
          <p className="label mb-1.5">Custo do lote</p>
          <p className="text-2xl font-bold leading-tight" style={{ color: config.color }}>
            {pricing.data ? formatMoney(pricing.data.total) : '...'}
          </p>
          <p className="mt-1 text-xs leading-snug text-ink-3">
            {pricing.data
              ? `${games} volante(s) de ${formatMoney(pricing.data.per_game)}, com ${formatNumber(
                  pricing.data.combinations,
                )} jogos simples cada`
              : 'calculando'}
          </p>
        </div>

        {overBudget ? (
          <Alert tone="warning">
            O lote de {formatMoney(total)} passa do orcamento de {formatMoney(budgetValue ?? 0)}. A
            geracao sera recusada com esse limite.
          </Alert>
        ) : null}

        <button
          type="button"
          className="btn-primary w-full py-2.5"
          onClick={submit}
          disabled={generator.isPending}
        >
          {generator.isPending ? 'Gerando' : 'Gerar jogos'}
        </button>
      </Panel>

      <div className="space-y-5">
        {error ? (
          <Alert tone="danger" title={error.problem?.title ?? 'Falha na geracao'}>
            {error.message}
          </Alert>
        ) : null}

        {generator.isSuccess ? (
          <>
            <Panel
              title={`${generator.data.games.length} jogos gerados`}
              hint={`Seed ${generator.data.seed}. Repita a seed para reproduzir exatamente este lote.`}
              actions={
                <div className="text-right">
                  <p className="text-xs uppercase tracking-wide text-ink-3">Total</p>
                  <p className="text-xl font-bold leading-tight" style={{ color: config.color }}>
                    {formatMoney(generator.data.cost.total)}
                  </p>
                </div>
              }
            >
              <div className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface-2 p-3">
                <label className="label mb-0 whitespace-nowrap" htmlFor="contest">
                  Concurso da aposta
                </label>
                <input
                  id="contest"
                  type="number"
                  min={1}
                  placeholder="ex.: 3057"
                  value={contestNo}
                  onChange={(event) => setContestNo(event.target.value)}
                  className="input max-w-[160px]"
                />
                <span className="text-xs leading-snug text-ink-3">
                  preencha para liberar o botao Registrar de cada jogo
                </span>
              </div>

              <ul className="mt-4 divide-y divide-line-soft">
                {generator.data.games.map((game, index) => (
                  <li
                    key={game.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <span className="w-5 shrink-0 text-xs font-bold text-ink-3">
                        {index + 1}
                      </span>
                      {game.extras?.columns ? (
                        <span className="font-mono text-base font-bold tracking-widest text-ink-2">
                          {game.extras.columns.map((column) => column.join('')).join(' ')}
                        </span>
                      ) : (
                        game.numbers.map((value) => (
                          <NumberBall
                            key={value}
                            value={value}
                            tone="selected"
                            color={config.color}
                            size="sm"
                          />
                        ))
                      )}
                      {typeof game.extras?.month === 'number' ? (
                        <Badge color={config.accent}>{MONTH_NAMES[game.extras.month - 1]}</Badge>
                      ) : null}
                      {game.already_drawn ? <Badge color="var(--neg)">ja sorteado</Badge> : null}
                    </div>

                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        className="btn-ghost px-3 py-1.5"
                        onClick={() => setOpenGameId(game.id)}
                      >
                        Detalhes
                      </button>
                      <button
                        type="button"
                        className="btn-ghost px-3 py-1.5"
                        disabled={
                          contestNo.trim() === '' || createBet.isPending || registered.has(game.id)
                        }
                        onClick={() =>
                          createBet.mutate(
                            { game_id: game.id, contest_no: Number(contestNo) },
                            {
                              onSuccess: () =>
                                setRegistered((atual) => new Set(atual).add(game.id)),
                            },
                          )
                        }
                      >
                        {registered.has(game.id) ? 'Registrada' : 'Registrar'}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>

              {registered.size ? (
                <p className="mt-4 text-sm text-pos">
                  {registered.size === 1
                    ? '1 aposta registrada'
                    : `${registered.size} apostas registradas`}{' '}
                  no concurso {contestNo}. Elas aparecem na aba Meus jogos.
                </p>
              ) : null}
            </Panel>
          </>
        ) : (
          <Panel
            title="Nenhum lote gerado nesta sessao"
            hint="Escolha os parametros ao lado e gere o lote"
          >
            {config.boardKind === 'columns' ? (
              <div className="flex justify-center py-2">
                <ColumnsBoard config={config} />
              </div>
            ) : (
              <EmptyState
                title="O resultado aparece aqui"
                description="A resposta traz apenas as dezenas e a marca de combinacao ja sorteada. O detalhamento vem sob demanda, ao abrir um jogo."
              />
            )}
          </Panel>
        )}
      </div>

      {openGameId ? (
        <InsightPanel config={config} gameId={openGameId} onClose={() => setOpenGameId(null)} />
      ) : null}
    </div>
  )
}
