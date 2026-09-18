# Lotto Lab - redesenho aplicado

Arquivos gerados a partir do protótipo aprovado. As assinaturas dos componentes
existentes foram mantidas, então as telas de feature continuam compilando sem
alteração: o que muda é o visual, não a API.

## Substituir

| Arquivo | O que muda |
| --- | --- |
| `web/src/index.css` | Tokens de tema claro/escuro e todas as classes de componente (.card, .btn, .tab, .label, .input, .pill) reescritas sobre os tokens |
| `web/tailwind.config.js` | Fontes Instrument Sans + JetBrains Mono, cores mapeadas nos tokens, darkMode por `data-theme` |
| `web/src/app/Layout.tsx` | Sidebar recolhível e persistente, cabeçalho por rota, troca de tema |
| `web/src/shared/ui/NumberBall.tsx` | Seis estados sobre tokens, três tamanhos, anel de foco e estado riscado |
| `web/src/shared/ui/primitives.tsx` | Panel/StatCard redesenhados; novos: Modal, Drawer, Segmented, Pills, Row, StatusChip |

## Adicionar

| Arquivo | O que é |
| --- | --- |
| `web/src/shared/ui/theme.ts` | `useTheme` (segue o sistema até a primeira escolha manual) e `useSidebar` (estado recolhido persiste) |

## Notas de integração

1. **Cor da modalidade.** O `Layout` injeta `--mod` quando a rota é `/m/:slug`.
   Qualquer elemento abaixo dele usa `bg-mod`, `text-mod` ou `.btn-mod` sem
   receber a cor por prop. Fora de uma modalidade o token cai no verde da
   Mega-Sena; se preferir neutro, troque o fallback em `index.css`.
2. **Fontes.** Vêm por `@import` no topo do `index.css`. Se preferir
   auto-hospedar, remova o import e sirva os arquivos woff2 — os nomes das
   famílias no `tailwind.config.js` não mudam.
3. **Tema.** `useTheme` grava `data-theme` no `<html>`. Para evitar o flash de
   tema claro no primeiro paint, adicione ao `index.html`, antes do bundle:

   ```html
   <script>
     document.documentElement.dataset.theme =
       localStorage.getItem('lotto.theme') ||
       (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
   </script>
   ```
4. **NumberBall** ganhou `size="xs"`, `ring` e `struck`. Os valores antigos
   (`sm`, `md`) continuam válidos, só ficaram 3px menores para a densidade nova.
5. **Tailwind 3.4+** é necessário para a sintaxe `darkMode: ['variant', …]`. Em
   versões anteriores use `darkMode: 'class'` e troque `data-theme` por
   `class="dark"` no `theme.ts`.

## Ainda no protótipo, não nestes arquivos

As telas em si (Painel reorganizado, Análise em sub-abas, Gerador em quatro
passos com drawer de filtros, Importação com quatro estados) estão no protótipo
`Lotto Lab.dc.html`. Elas dependem dos seus hooks de dados reais, então valem
como referência de layout e hierarquia, não como código para colar. Com estes
cinco arquivos no lugar, cada tela pode ser migrada uma por vez sem quebrar as
outras.
