import { pad } from '@/shared/lib/format'

export type BallTone = 'default' | 'selected' | 'hot' | 'cold' | 'overdue' | 'hit'

/** Os seis estados da bolinha. Nenhum deles carrega cor literal: tudo vem dos tokens. */
const TONES: Record<BallTone, string> = {
  default: 'border-line bg-surface-1 text-ink-2',
  selected: 'border-transparent',
  hot: 'text-[var(--hot-fg)] border-[var(--hot-bd)] bg-[var(--hot-bg)]',
  cold: 'text-[var(--cold-fg)] border-[var(--cold-bd)] bg-[var(--cold-bg)]',
  overdue: 'text-[var(--late-fg)] border-[var(--late-bd)] bg-[var(--late-bg)]',
  hit: 'border-transparent bg-[var(--hit-bg)] text-[var(--hit-fg)]',
}

interface Props {
  value: number
  tone?: BallTone
  color?: string
  size?: 'xs' | 'sm' | 'md'
  title?: string
  /** Dezena vai com zero a esquerda; digito de coluna do Super Sete vai sozinho. */
  padded?: boolean
  /** Anel de foco, usado pela dezena inspecionada no volante de analise. */
  ring?: boolean
  struck?: boolean
  onClick?: () => void
}

export function NumberBall({
  value,
  tone = 'default',
  color,
  size = 'md',
  title,
  padded = true,
  ring = false,
  struck = false,
  onClick,
}: Props) {
  const dimension =
    size === 'xs'
      ? 'h-[23px] w-[23px] text-[10px]'
      : size === 'sm'
        ? 'h-[26px] w-[26px] text-[11px]'
        : 'h-[30px] w-[30px] text-xs'

  const style =
    tone === 'selected'
      ? { backgroundColor: color ?? 'var(--mod)', color: 'var(--mod-on)' }
      : undefined

  const Tag = onClick ? 'button' : 'span'

  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      title={title}
      className={`num inline-flex ${dimension} items-center justify-center rounded-full border font-semibold ${
        TONES[tone]
      } ${ring ? 'ring-[3px] ring-ink-3/40' : ''} ${struck ? 'line-through' : ''} ${
        onClick ? 'cursor-pointer' : ''
      }`}
      style={style}
    >
      {padded ? pad(value) : value}
    </Tag>
  )
}
