import { useEffect, type ReactNode } from 'react'

export function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
  accent,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'neutral' | 'positive' | 'negative'
  accent?: string
}) {
  const toneClass =
    tone === 'positive' ? 'text-pos' : tone === 'negative' ? 'text-neg' : 'text-ink-1'

  return (
    <div className="card flex min-w-0 flex-col">
      <div className="flex items-center gap-2">
        {accent ? (
          <span className="h-3 w-1 rounded-full" style={{ backgroundColor: accent }} />
        ) : null}
        <p className="label truncate">{label}</p>
      </div>
      <p className={`num mt-[7px] text-[21px] font-semibold leading-none ${toneClass}`}>{value}</p>
      {hint ? <p className="mt-[5px] text-[11px] leading-snug text-ink-3">{hint}</p> : null}
    </div>
  )
}

/**
 * Card com cabecalho e corpo. O cabecalho quebra em duas linhas quando aperta: o
 * titulo nunca cede espaco para a dica auxiliar.
 */
export function Panel({
  title,
  hint,
  actions,
  children,
  className = '',
  bodyClassName = '',
  scroll = false,
}: {
  title: ReactNode
  hint?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
  scroll?: boolean
}) {
  return (
    <section
      className={`flex min-w-0 flex-col overflow-hidden rounded-card border border-line bg-surface-1 shadow-card ${className}`}
    >
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2.5 border-b border-line px-4 py-3">
        <div className="min-w-0 flex-[1_1_200px]">
          <h3 className="text-[13px] font-semibold leading-tight text-ink-1">{title}</h3>
          {hint ? <p className="mt-0.5 text-[11px] leading-snug text-ink-3">{hint}</p> : null}
        </div>
        {actions ? <div className="flex flex-auto flex-wrap justify-end gap-2">{actions}</div> : null}
      </header>
      <div className={`min-h-0 min-w-0 flex-1 ${scroll ? 'scroll-area' : ''} ${bodyClassName}`}>
        {children}
      </div>
    </section>
  )
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="min-w-0">
      <h3 className="text-[13px] font-semibold leading-tight text-ink-1">{children}</h3>
      {hint ? <p className="mt-0.5 text-[11px] leading-snug text-ink-3">{hint}</p> : null}
    </div>
  )
}

export function Spinner({ label = 'Carregando' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-[12.5px] text-ink-3">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-[var(--mod)]" />
      {label}
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-surface-2 px-6 py-14 text-center">
      <p className="text-sm font-semibold text-ink-1">{title}</p>
      {description ? (
        <p className="mx-auto mt-[7px] max-w-[48ch] text-[12.5px] leading-relaxed text-ink-3">
          {description}
        </p>
      ) : null}
    </div>
  )
}

export function Alert({
  tone = 'info',
  title,
  children,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success'
  title?: string
  children: ReactNode
}) {
  const tones = {
    info: 'border-[var(--cold-bd)] bg-[var(--cold-bg)] text-[var(--cold-fg)]',
    warning: 'border-[var(--late-bd)] bg-[var(--late-bg)] text-[var(--late-fg)]',
    danger: 'border-neg/40 bg-neg/[0.07] text-neg',
    success: 'border-pos/40 bg-pos/[0.08] text-pos',
  } as const

  return (
    <div className={`rounded-[10px] border p-3.5 text-[12px] leading-relaxed ${tones[tone]}`}>
      {title ? <p className="mb-1 font-semibold">{title}</p> : null}
      {children}
    </div>
  )
}

export function Badge({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span
      className="num inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10.5px] font-semibold leading-5"
      style={{ backgroundColor: color ?? 'var(--s3)', color: color ? 'var(--mod-on)' : 'var(--ink3)' }}
    >
      {children}
    </span>
  )
}

/** Chip de estado: aguardando, premiada, sem premio. */
export function StatusChip({
  tone,
  children,
}: {
  tone: 'pending' | 'won' | 'closed'
  children: ReactNode
}) {
  const tones = {
    pending: 'border-[var(--late-bd)] bg-[var(--late-bg)] text-[var(--late-fg)]',
    won: 'border-pos/40 bg-pos/[0.14] text-pos',
    closed: 'border-line bg-surface-2 text-ink-3',
  } as const
  return (
    <span
      className={`inline-block rounded-full border px-2.5 py-[3px] text-[10.5px] font-semibold leading-tight ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="label mb-1.5">{label}</p>
      <div className="text-[12.5px] text-ink-2">{children}</div>
    </div>
  )
}

/** Par rotulo e valor em linha, usado em drawer e modal. */
export function Row({
  label,
  value,
  tone,
}: {
  label: ReactNode
  value: ReactNode
  tone?: 'positive' | 'negative'
}) {
  const color = tone === 'positive' ? 'text-pos' : tone === 'negative' ? 'text-neg' : 'text-ink-1'
  return (
    <span className="flex items-baseline justify-between gap-3.5 border-b border-line-soft pb-2.5">
      <span className="text-[11.5px] leading-snug text-ink-3">{label}</span>
      <span className={`num text-right text-[12.5px] font-semibold ${color}`}>{value}</span>
    </span>
  )
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { key: T; label: string }[]
  onChange: (key: T) => void
}) {
  return (
    <div className="flex gap-1.5">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          onClick={() => onChange(option.key)}
          className={`flex-1 rounded-[7px] border px-1.5 py-1.5 text-[11px] font-semibold leading-tight ${
            value === option.key
              ? 'border-line bg-surface-3 text-ink-1'
              : 'border-transparent bg-transparent text-ink-3 hover:bg-surface-2'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export function Pills<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { key: T; label: string }[]
  onChange: (key: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          onClick={() => onChange(option.key)}
          className={`pill ${value === option.key ? 'pill-active' : ''}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

function useEscape(onClose: () => void) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
}

/** Janela lateral: ficha de dezena, filtros do gerador, detalhe de jogo. */
export function Drawer({
  open,
  title,
  hint,
  footer,
  onClose,
  children,
}: {
  open: boolean
  title: ReactNode
  hint?: ReactNode
  footer?: ReactNode
  onClose: () => void
  children: ReactNode
}) {
  useEscape(onClose)
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-[rgba(10,14,18,0.44)]">
      <button type="button" aria-label="Fechar" onClick={onClose} className="absolute inset-0" />
      <aside className="relative flex h-full w-[420px] max-w-[92vw] flex-col border-l border-line bg-surface-1 shadow-float">
        <div className="flex items-start gap-3 border-b border-line p-4">
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold leading-snug text-ink-1">{title}</span>
            {hint ? (
              <span className="mt-0.5 block text-[11.5px] leading-snug text-ink-3">{hint}</span>
            ) : null}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="num h-[26px] w-[26px] shrink-0 rounded-[7px] border border-line bg-surface-2 text-xs font-semibold text-ink-2"
          >
            {'\u2715'}
          </button>
        </div>
        <div className="scroll-area flex min-h-0 flex-1 flex-col gap-3.5 p-4">{children}</div>
        {footer ? (
          <div className="flex items-center gap-2.5 border-t border-line bg-surface-2 px-4 py-3.5">
            {footer}
          </div>
        ) : null}
      </aside>
    </div>
  )
}

/** Janela central: volante do gerador, perfil, seed, registrar, conferencia. */
export function Modal({
  open,
  title,
  hint,
  width = 520,
  footer,
  onClose,
  children,
}: {
  open: boolean
  title: ReactNode
  hint?: ReactNode
  width?: number
  footer?: ReactNode
  onClose: () => void
  children: ReactNode
}) {
  useEscape(onClose)
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-[rgba(10,14,18,0.5)] p-6">
      <button type="button" aria-label="Fechar" onClick={onClose} className="absolute inset-0" />
      <section
        className="relative flex max-h-full w-full flex-col overflow-hidden rounded-[14px] border border-line bg-surface-1 shadow-float"
        style={{ maxWidth: width }}
      >
        <div className="flex items-start gap-3 border-b border-line px-[18px] py-4">
          <span className="min-w-0 flex-1">
            <span className="block text-[15px] font-semibold leading-snug text-ink-1">{title}</span>
            {hint ? (
              <span className="mt-0.5 block text-[11.5px] leading-snug text-ink-3">{hint}</span>
            ) : null}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="num h-[26px] w-[26px] shrink-0 rounded-[7px] border border-line bg-surface-2 text-xs font-semibold text-ink-2"
          >
            {'\u2715'}
          </button>
        </div>
        <div className="scroll-area flex min-h-0 flex-1 flex-col gap-4 p-[18px]">{children}</div>
        {footer ? (
          <div className="flex items-center gap-2.5 border-t border-line bg-surface-2 px-[18px] py-3.5">
            {footer}
          </div>
        ) : null}
      </section>
    </div>
  )
}
