import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { MODALITY_LIST, modalityFromSlug } from '@/config/modalities'
import { useHealth } from '@/shared/hooks/queries'
import { useSidebar, useTheme } from '@/shared/ui/theme'

function NavItem({
  to,
  end,
  label,
  dot,
  meta,
  open,
}: {
  to: string
  end?: boolean
  label: string
  dot: string
  meta?: string
  open: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      title={label}
      className={({ isActive }) =>
        `flex w-full items-center gap-[9px] rounded-lg border px-2 py-[7px] text-left text-[12.5px] font-medium leading-[1.3] ${
          open ? 'justify-start' : 'justify-center'
        } ${
          isActive
            ? 'border-line bg-surface-3 text-ink-1'
            : 'border-transparent text-ink-2 hover:bg-surface-2'
        }`
      }
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: dot }} />
      {/* Recolhida, a sidebar mostra so o ponto: rotulo cortado nao se le. */}
      {open ? <span className="min-w-0 flex-1 truncate">{label}</span> : null}
      {open && meta ? <span className="num shrink-0 text-[10px] text-ink-3">{meta}</span> : null}
    </NavLink>
  )
}

function GroupLabel({ children, open }: { children: string; open: boolean }) {
  if (!open) return null
  return <span className="label px-1.5 pb-1 pt-3.5">{children}</span>
}

export function Layout() {
  const health = useHealth()
  const { theme, choose } = useTheme()
  const { open, toggle } = useSidebar()
  const location = useLocation()

  const slug = location.pathname.startsWith('/m/') ? location.pathname.split('/')[2] : undefined
  const modality = modalityFromSlug(slug)
  const head = modality
    ? { title: modality.label, sub: modality.tagline, accent: modality.color }
    : location.pathname.startsWith('/bets')
      ? {
          title: 'Conferencia de apostas',
          sub: 'Todas as apostas registradas e o resultado de cada uma',
          accent: 'var(--ink1)',
        }
      : {
          title: 'Painel',
          sub: 'Visao geral do proximo sorteio, do dinheiro e do historico importado',
          accent: 'var(--ink1)',
        }

  const apiOk = health.data?.status === 'ok'

  return (
    <div
      className="flex min-h-screen bg-bg text-ink-1"
      style={modality ? { ['--mod' as string]: modality.color } : undefined}
    >
      <aside
        className="sticky top-0 flex h-screen shrink-0 flex-col gap-1 self-start overflow-hidden border-r border-line bg-surface-1 px-2.5 py-3.5 transition-[width] duration-150"
        style={{ width: open ? 218 : 62 }}
      >
        {/* Recolhida a linha empilha, senao o botao de alternar sai dos 62px. */}
        <div
          className={`flex items-center justify-center gap-2.5 px-1 pb-3.5 pt-0.5 ${
            open ? 'flex-row' : 'flex-col'
          }`}
        >
          <span className="num inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] bg-ink-1 text-[11px] font-bold text-surface-1">
            LL
          </span>
          {open ? (
            <span className="min-w-0 flex-1">
              <span className="block text-[13.5px] font-semibold leading-tight text-ink-1">
                Lotto Lab
              </span>
              <span className="block text-[10.5px] leading-tight text-ink-3">
                Analise de loterias
              </span>
            </span>
          ) : null}
          <button
            type="button"
            onClick={toggle}
            title={open ? 'Recolher navegacao' : 'Expandir navegacao'}
            className="num inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-line bg-surface-2 text-[11px] font-semibold text-ink-3 hover:text-ink-1"
          >
            {open ? '\u00ab' : '\u00bb'}
          </button>
        </div>

        <GroupLabel open={open}>Geral</GroupLabel>
        <NavItem to="/" end label="Painel" dot="var(--ink3)" open={open} />
        <NavItem to="/bets" label="Conferencia" dot="var(--ink3)" open={open} />

        <GroupLabel open={open}>Modalidades</GroupLabel>
        {MODALITY_LIST.map((item) => (
          <NavItem
            key={item.key}
            to={`/m/${item.slug}`}
            label={item.label}
            dot={item.color}
            open={open}
          />
        ))}

        <span className="flex-1" />

        <div className="flex flex-wrap items-center gap-1.5 border-t border-line-soft px-1 pb-0.5 pt-2.5">
          {(['light', 'dark'] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => choose(value)}
              title={value === 'light' ? 'Tema claro' : 'Tema escuro'}
              className={`flex-auto overflow-hidden whitespace-nowrap rounded-[7px] border px-2 py-1.5 text-[11px] font-semibold leading-tight ${
                theme === value
                  ? 'border-line bg-surface-3 text-ink-1'
                  : 'border-line-soft bg-transparent text-ink-3'
              }`}
            >
              {/* Recolhida nao cabe palavra: vai glifo. */}
              {open ? (value === 'light' ? 'Claro' : 'Escuro') : value === 'light' ? '\u2600' : '\u263e'}
            </button>
          ))}
        </div>
        {open ? (
          <div className="flex items-center gap-[7px] px-1.5 pt-1.5 text-[10.5px] leading-tight text-ink-3">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: apiOk ? 'var(--pos)' : 'var(--late-fg)' }}
            />
            <span>
              {health.isLoading ? 'verificando API' : apiOk ? 'API no ar' : 'API indisponivel'}
              {' \u00b7 '}
              IA {health.data?.ai_available ? 'disponivel' : 'desligada'}
            </span>
          </div>
        ) : null}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3.5 border-b border-line bg-surface-1 px-5">
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <span
              className="h-[18px] w-[3px] shrink-0 rounded-sm"
              style={{ background: head.accent }}
            />
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold leading-tight text-ink-1">
                {head.title}
              </span>
              <span className="block truncate text-[11px] leading-tight text-ink-3">
                {head.sub}
              </span>
            </span>
          </div>
        </header>

        <main className="flex min-w-0 flex-1 flex-col gap-3.5 px-5 pb-11 pt-[18px]">
          <Outlet />
        </main>

        <footer className="px-5 pb-8 text-[11px] leading-relaxed text-ink-3">
          Loteria e sorteio aleatorio. O Lotto Lab descreve o que o historico mostra e o quanto cada
          jogo e coerente com esse historico. Nao existe previsao de resultado.
        </footer>
      </div>
    </div>
  )
}
