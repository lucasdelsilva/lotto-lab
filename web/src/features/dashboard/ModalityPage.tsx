import { useState } from 'react'

import { AnalysisTab } from '@/features/analysis/AnalysisTab'
import { MyGamesTab } from '@/features/bets/MyGamesTab'
import { GeneratorTab } from '@/features/generator/GeneratorTab'
import { ImportTab } from '@/features/import/ImportTab'
import { MONTH_NAMES } from '@/config/modalities'
import { useLatestDraw, useModalityConfig } from '@/shared/hooks/queries'
import { formatDate, formatMoney } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'

const TABS = [
  { id: 'import', label: 'Importar' },
  { id: 'analysis', label: 'Analise' },
  { id: 'generator', label: 'Gerador' },
  { id: 'games', label: 'Meus jogos' },
] as const

type TabId = (typeof TABS)[number]['id']

export function ModalityPage() {
  const config = useModalityConfig()
  const [tab, setTab] = useState<TabId>('analysis')
  const latest = useLatestDraw(config.key)
  const month = latest.data?.extras?.month

  return (
    <div className="space-y-6">
      <section
        className="rounded-xl px-7 py-7 text-white shadow-sm"
        style={{ background: `linear-gradient(110deg, ${config.color}, ${config.accent})` }}
      >
        <h2 className="text-3xl font-bold leading-tight">{config.label}</h2>
        <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-white/85">{config.tagline}</p>

        <dl className="mt-6 grid gap-x-10 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-wide text-white/70">
              Ultimo concurso importado
            </dt>
            <dd className="mt-0.5 text-lg font-semibold">
              {latest.data ? latest.data.contest_no : 'nenhum'}
              {latest.data ? (
                <span className="ml-2 text-sm font-normal text-white/80">
                  {formatDate(latest.data.drawn_at)}
                </span>
              ) : null}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-white/70">Aposta minima</dt>
            <dd className="mt-0.5 text-lg font-semibold">
              {config.minPick} numeros por {formatMoney(config.basePrice)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-white/70">Universo</dt>
            <dd className="mt-0.5 text-lg font-semibold">
              {config.boardKind === 'columns'
                ? `${config.columns} colunas de 0 a 9`
                : `${config.universeMin} a ${config.universeMax}`}
            </dd>
          </div>
        </dl>

        {latest.data ? (
          <div className="mt-5 flex flex-wrap items-center gap-1.5 border-t border-white/20 pt-5">
            {latest.data.numbers.map((value, index) => (
              <NumberBall
                key={`${value}-${index}`}
                value={value}
                size="sm"
                padded={config.boardKind !== 'columns'}
              />
            ))}
            {typeof month === 'number' ? (
              <span className="ml-2 rounded-full bg-white/20 px-3 py-1 text-xs font-semibold">
                Mes da sorte: {MONTH_NAMES[month - 1]}
              </span>
            ) : null}
          </div>
        ) : null}
      </section>

      {/* .tab virou pilula: o trilho de sublinhado e o -mb-px que o encostava sairam. */}
      <div>
        <nav className="flex flex-wrap gap-1">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`tab ${tab === item.id ? 'tab-active' : ''}`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      {/*
       * A key por modalidade e o que mantem uma modalidade isolada da outra. As cinco
       * compartilham a rota /m/:modality, entao o React reaproveita a mesma instancia ao
       * trocar de modalidade: sem a key, o lote gerado na Mega-Sena continuava na tela da
       * Lotofacil, junto com o contador de dezenas, o resultado da importacao e o aviso de
       * aposta registrada. Trocar a key descarta esse estado.
       */}
      {tab === 'import' ? <ImportTab key={config.key} config={config} /> : null}
      {tab === 'analysis' ? <AnalysisTab key={config.key} config={config} /> : null}
      {tab === 'generator' ? <GeneratorTab key={config.key} config={config} /> : null}
      {tab === 'games' ? <MyGamesTab key={config.key} config={config} /> : null}
    </div>
  )
}
