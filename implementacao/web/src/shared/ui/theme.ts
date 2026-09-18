import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'lotto.theme'

function systemTheme(): Theme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function stored(): Theme | null {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

/**
 * Tema aplicado em data-theme no <html>. Sem escolha salva o app segue o sistema
 * e continua seguindo em tempo real; a primeira escolha manual congela a preferencia.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => stored() ?? systemTheme())
  const [pinned, setPinned] = useState(() => stored() !== null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    if (pinned || !window.matchMedia) return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event: MediaQueryListEvent) => setTheme(event.matches ? 'dark' : 'light')
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [pinned])

  const choose = useCallback((next: Theme) => {
    setTheme(next)
    setPinned(true)
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* modo privado: a escolha vale so para a sessao */
    }
  }, [])

  return { theme, choose }
}

const NAV_KEY = 'lotto.nav'

/** Sidebar recolhida persiste entre recargas. */
export function useSidebar() {
  const [open, setOpen] = useState(() => {
    try {
      return localStorage.getItem(NAV_KEY) !== 'closed'
    } catch {
      return true
    }
  })

  const toggle = useCallback(() => {
    setOpen((previous) => {
      const next = !previous
      try {
        localStorage.setItem(NAV_KEY, next ? 'open' : 'closed')
      } catch {
        /* ignora */
      }
      return next
    })
  }, [])

  return { open, toggle }
}
