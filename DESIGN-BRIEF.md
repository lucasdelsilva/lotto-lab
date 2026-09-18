# Brief de design do Lotto Lab

Documento de referencia para redesenhar a interface. A primeira parte descreve o sistema
como ele e hoje.

---

## Parte 1: o sistema

### O que e

Painel web de analise estatistica e geracao de jogos para as cinco loterias da Caixa
Economica Federal. Uso pessoal, um unico usuario, sem login. Roda local.

O fluxo do usuario e sempre o mesmo: importar a planilha oficial de resultados, olhar a
analise do historico, gerar jogos com filtros estatisticos, registrar o que apostou e
conferir os acertos depois do sorteio.

### Modalidades e cores de marca

Cada modalidade tem a cor oficial da Caixa. **Essas cores sao obrigatorias e identificam a
modalidade em toda a interface.** O usuario reconhece a tela pela cor antes de ler o titulo.

| Modalidade | Cor principal | Cor de apoio | Volante |
|---|---|---|---|
| Mega-Sena | `#209869` verde | `#0b6b48` | 60 dezenas, grade 6 x 10 |
| Lotofacil | `#930989` roxo | `#6b0664` | 25 dezenas, grade 5 x 5 |
| Quina | `#260085` azul escuro | `#180058` | 80 dezenas, grade 8 x 10 |
| Dia de Sorte | `#CB8E4E` dourado | `#8f6233` | 31 dezenas, grade 4 x 8, mais mes da sorte |
| Super Sete | `#A8CF45` verde limao | `#6f8f1f` | 7 colunas de digitos 0 a 9 |

### Mapa de telas

Sao tres rotas apenas.

**`/` Painel**
Visao geral do dinheiro. Quatro indicadores no topo (gasto no mes, total investido, total
retornado, saldo), cinco cartoes de atalho para as modalidades, duas listas lado a lado
(apostas pendentes, ultimos lotes gerados) e uma tabela de apostas conferidas.

**`/m/:modality` Modalidade**
A tela principal, onde o usuario passa o tempo. Cabecalho colorido com o nome da
modalidade, o ultimo concurso importado com as dezenas sorteadas, a aposta minima e o
universo. Abaixo, quatro abas:

1. **Importar**: area de arrastar arquivo, aviso de que a importacao substitui todo o
   historico da modalidade, tabela de erros por linha quando o arquivo e invalido, previa
   dos dez concursos mais recentes e historico de importacoes na lateral.
2. **Analise**: a aba mais densa. Quatro indicadores, grafico de barras de frequencia por
   dezena com alternancia para atraso, tres listas de dezenas (quentes, frias, atrasadas),
   histograma de soma, distribuicao de pares e impares, mapa de calor de atraso com 60
   linhas, tabela de pares com maior lift, tabela de faixas por metrica e um bloco de
   sequencias.
3. **Gerador**: barra lateral fixa com os parametros (quantidade de numeros, jogos, seed,
   perfil, orcamento, lista de filtros com checkbox e percentual de eficiencia) e, ao lado,
   a lista de jogos gerados. Clicar num jogo abre um painel lateral com o detalhamento.
4. **Meus jogos**: formulario de registro manual com volante clicavel, e a lista de apostas
   da modalidade com os acertos destacados.

**`/bets` Conferencia**
Tres indicadores, filtros de modalidade e situacao, tabela de gasto por modalidade e mes, e
a lista de todas as apostas.

### Componentes que se repetem

- **Bolinha de dezena** (`NumberBall`): circulo com o numero. Tem seis estados visuais:
  neutro, selecionado (recebe a cor da modalidade), quente (vermelho), frio (azul),
  atrasado (ambar) e acertou (verde).
- **Volante de dezenas** (`NumbersBoard`): grade com o numero de colunas do volante fisico
  da modalidade, montada com as bolinhas. Clicavel no registro manual.
- **Volante de colunas** (`ColumnsBoard`): exclusivo do Super Sete. Sete colunas numeradas,
  cada uma com os digitos de 0 a 9 na vertical.
- **Cartao de indicador** (`StatCard`): rotulo pequeno em caixa alta, numero grande, dica
  em texto menor.
- **Painel** (`Panel`): cartao com titulo, subtitulo explicativo, acoes no canto direito e
  corpo que rola por dentro quando o conteudo e longo.
- **Alerta**: quatro tons (informacao, aviso, erro, sucesso).
- **Etiqueta** (`Badge`): pilula colorida pequena, usada para modalidade, situacao da
  aposta e marca de jogo ja sorteado.

### Stack visual atual

Tailwind CSS, Recharts para os graficos, React 18 com TypeScript. Tema claro apenas.
Fundo cinza muito claro, cartoes brancos com borda fina e sombra leve, cantos arredondados.
Fonte do sistema.

### O que precisa sobreviver ao redesenho

1. **Uma unica tela de modalidade.** As cinco modalidades usam a mesma tela, dirigida por um
   arquivo de configuracao. Nao existem cinco telas. O que muda entre elas e a cor, o
   volante, os limites e os campos extras.
2. **O Super Sete e a excecao.** O volante dele e de colunas, nao de dezenas, e a analise
   dele e uma matriz 7 x 10. Precisa de tratamento visual proprio dentro da mesma tela.
3. **A metafora do volante.** As dezenas sao sempre bolinhas em grade, como no volante de
   papel da Caixa. E assim que o usuario confere um jogo.
4. **Densidade de dados na aba Analise.** Sao muitos numeros de proposito. O desafio de
   design e organizar, nao reduzir.
5. **Rotulos em portugues** e valores em formato brasileiro: `R$ 1.260,00`, `15/09/2026`.

### Problemas do design atual que valem resolver

- A aba Analise e uma pilha longa de cartoes sem hierarquia clara. O usuario rola muito para
  achar o que quer.
- O mapa de calor de atraso tem 60 linhas e e dificil de ler.
- A barra lateral do gerador ficou comprida demais depois que os filtros entraram, com onze
  checkboxes empilhados.
- O painel de detalhe do jogo abre por cima de tudo e tem informacao demais de uma vez.
- Nao existe tema escuro.
- A tela do painel inicial e pouco util: mostra dinheiro, mas nao mostra o que o usuario
  mais quer saber, que e quando sai o proximo sorteio e o que ele tem apostado nele.

---

## Parte 2: prompt para o Claude Design

### Qual opcao escolher

Use **UI mockups**.

E a opcao feita para desenhar interface de aplicacao em multiplas telas, que e exatamente o
caso. As outras nao servem: *Wireframe* entrega so a estrutura em baixa fidelidade, sem cor
nem tipografia, e a cor de marca por modalidade e parte central do problema aqui.
*Mobile app design* assume telas de celular, mas este e um painel denso de desktop.
*Document*, *Slides*, *Diagram* e o resto sao outros formatos de entrega.

Se quiser resolver a estrutura antes do visual, comece por *Wireframe* e depois refaca em
*UI mockups*. Para ir direto ao resultado, va de *UI mockups*.