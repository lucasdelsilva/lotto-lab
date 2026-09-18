/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // O tema escuro e dirigido pelo atributo data-theme no <html>, nao por classe.
  darkMode: ['variant', '&:where([data-theme="dark"], [data-theme="dark"] *)'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Tokens do tema, resolvidos em index.css
        bg: 'var(--bg)',
        surface: { 1: 'var(--s1)', 2: 'var(--s2)', 3: 'var(--s3)' },
        line: { DEFAULT: 'var(--bd)', soft: 'var(--bd2)' },
        ink: { 1: 'var(--ink1)', 2: 'var(--ink2)', 3: 'var(--ink3)' },
        mod: { DEFAULT: 'var(--mod)', on: 'var(--mod-on)' },
        pos: 'var(--pos)',
        neg: 'var(--neg)',
        // Cores oficiais da Caixa, mantidas para graficos e marca
        'caixa-blue': '#005ca9',
        'caixa-teal': '#0f9d63',
        'caixa-ink': '#10151b',
      },
      boxShadow: { card: 'var(--sh)', float: 'var(--shz)' },
      borderRadius: { card: '0.75rem' },
    },
  },
  plugins: [],
}
