import type { ModalityConfig } from '@/config/modalities'
import { universeOf } from '@/config/modalities'
import { NumberBall, type BallTone } from './NumberBall'

interface BoardProps {
  config: ModalityConfig
  selected?: number[]
  highlights?: Record<number, BallTone>
  onToggle?: (value: number) => void
  size?: 'sm' | 'md'
}

/** Volante de dezenas, com o mesmo numero de colunas do volante fisico da modalidade. */
export function NumbersBoard({ config, selected = [], highlights, onToggle, size = 'md' }: BoardProps) {
  const chosen = new Set(selected)

  return (
    <div
      className="grid gap-1.5"
      style={{ gridTemplateColumns: `repeat(${config.boardCols}, minmax(0, 1fr))` }}
    >
      {universeOf(config).map((value) => {
        const tone: BallTone = chosen.has(value) ? 'selected' : (highlights?.[value] ?? 'default')
        return (
          <NumberBall
            key={value}
            value={value}
            tone={tone}
            color={config.color}
            size={size}
            onClick={onToggle ? () => onToggle(value) : undefined}
          />
        )
      })}
    </div>
  )
}

interface ColumnsBoardProps {
  config: ModalityConfig
  selected?: number[][]
  onToggle?: (column: number, digit: number) => void
  highlights?: number[]
  size?: 'sm' | 'md'
}

/**
 * Volante do Super Sete. Sete colunas independentes de 0 a 9, e nao uma cartela de
 * dezenas: e a unica excecao estrutural do projeto, injetada pela config da modalidade.
 */
export function ColumnsBoard({
  config,
  selected = [],
  onToggle,
  highlights,
  size = 'md',
}: ColumnsBoardProps) {
  const digits = Array.from({ length: 10 }, (_, index) => index)

  return (
    <div className="inline-block">
      <div
        className="mb-2 rounded px-3 py-1 text-center text-xs font-bold uppercase tracking-[0.3em] text-white"
        style={{ backgroundColor: config.accent }}
      >
        Colunas
      </div>
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${config.columns}, minmax(0, 1fr))` }}>
        {Array.from({ length: config.columns }, (_, column) => (
          <div key={column} className="flex flex-col items-center gap-1.5">
            <span
              className="mb-1 flex h-6 w-6 items-center justify-center rounded text-xs font-bold text-white"
              style={{ backgroundColor: config.color }}
            >
              {column + 1}
            </span>
            {digits.map((digit) => {
              const isSelected = selected[column]?.includes(digit) ?? false
              const isDrawn = highlights?.[column] === digit
              const tone: BallTone = isSelected ? 'selected' : isDrawn ? 'hit' : 'default'
              return (
                <NumberBall
                  key={digit}
                  value={digit}
                  tone={tone}
                  color={config.color}
                  size={size}
                  padded={false}
                  onClick={onToggle ? () => onToggle(column, digit) : undefined}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
