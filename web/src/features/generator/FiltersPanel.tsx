import type { ModalityConfig } from '@/config/modalities'
import type { FilterEfficiencyRow, FilterId } from '@/shared/api/types'
import { useFilterCatalog, useFilterEfficiency } from '@/shared/hooks/queries'
import { Spinner } from '@/shared/ui/primitives'

/**
 * Lista de filtros da modalidade, montada pelo catalogo que o back devolve. Cada filtro
 * mostra a propria eficiencia: o percentual dos ultimos concursos reais que passariam
 * nele. Eficiencia baixa significa filtro que corta ate resultado que de fato saiu.
 */
export function FiltersPanel({
  config,
  enabled,
  onToggle,
  onToggleAll,
}: {
  config: ModalityConfig
  enabled: Set<FilterId>
  onToggle: (id: FilterId) => void
  onToggleAll: (ids: FilterId[], value: boolean) => void
}) {
  const catalog = useFilterCatalog(config.key)
  const efficiency = useFilterEfficiency(config.key, 200)

  if (catalog.isLoading) return <Spinner label="Carregando filtros" />
  if (!catalog.data) return null

  const rows = catalog.data.filters
  const ids = rows.map((item) => item.id)
  const todosLigados = ids.every((id) => enabled.has(id))
  const porId = new Map<FilterId, FilterEfficiencyRow>(
    (efficiency.data?.filters ?? []).map((item) => [item.id, item]),
  )

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <span className="label mb-0">
          Filtros de {config.label}
          <span className="ml-1 font-normal normal-case tracking-normal text-ink-3">
            ({enabled.size} de {rows.length})
          </span>
        </span>
        <button
          type="button"
          className="text-xs font-semibold text-caixa-blue hover:underline"
          onClick={() => onToggleAll(ids, !todosLigados)}
        >
          {todosLigados ? 'desmarcar todos' : 'marcar todos'}
        </button>
      </div>

      <div className="space-y-1">
        {rows.map((item) => {
          const eficiencia = porId.get(item.id)
          const ligado = enabled.has(item.id)
          return (
            <label
              key={item.id}
              title={item.description}
              className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2 transition ${
                ligado
                  ? 'border-line bg-surface-1'
                  : 'border-transparent bg-surface-2 text-ink-3'
              }`}
            >
              <input
                type="checkbox"
                checked={ligado}
                onChange={() => onToggle(item.id)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-caixa-blue"
              />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium leading-snug">{item.label}</span>
                  {eficiencia ? (
                    <span
                      className={`shrink-0 text-[11px] font-semibold ${
                        eficiencia.efficiency >= 0.85
                          ? 'text-pos'
                          : eficiencia.efficiency >= 0.7
                            ? 'text-[var(--late-fg)]'
                            : 'text-neg'
                      }`}
                      title={`${eficiencia.approved} dos ultimos ${eficiencia.total} concursos passariam neste filtro`}
                    >
                      {Math.round(eficiencia.efficiency * 100)}%
                    </span>
                  ) : null}
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-ink-3">
                  {item.description}
                </span>
              </span>
            </label>
          )
        })}
      </div>

      {efficiency.data ? (
        <p className="mt-2 text-xs leading-snug text-ink-3">
          O percentual ao lado de cada filtro e quantos dos ultimos {efficiency.data.sample}{' '}
          concursos reais passariam nele. Media geral de{' '}
          {Math.round(efficiency.data.overall * 100)}%. Filtro com percentual baixo esta
          cortando ate resultado que saiu, e vale desligar.
        </p>
      ) : null}
    </div>
  )
}
