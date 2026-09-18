# Lotto Lab

Micro-serviço de análise estatística e geração de jogos para as loterias da Caixa Econômica
Federal, com painel web próprio.

O fluxo é sempre o mesmo: importar o histórico oficial da modalidade, calcular estatísticas
profundas sobre esse histórico, gerar jogos usando essas estatísticas como critério,
controlar quanto foi gasto e conferir os resultados.

> Loteria é sorteio aleatório. Nada aqui prevê resultado. O que o sistema faz é descrever o
> histórico observado e medir o quanto um jogo é coerente com esse histórico.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Análise numérica | NumPy, Pandas |
| Banco | PostgreSQL 16 |
| ORM e migrations | SQLAlchemy 2.0 tipado, Alembic |
| Planilhas | openpyxl, csv |
| IA | SDK oficial da OpenAI, Structured Outputs com `json_schema` estrito |
| Front | Vite, React 18, TypeScript strict, Tailwind, TanStack Query, React Router |
| Gráficos | Recharts |
| Infra | Docker Compose |
| Testes | pytest no back, Vitest no front |
| Qualidade | ruff e mypy strict no back, eslint e prettier no front |

---

## Subir tudo

```bash
cp .env.example .env
docker compose up
```

| Serviço | Endereço |
|---|---|
| Painel web | http://localhost:5173 |
| API | http://localhost:8000/api |
| Documentação da API | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |
| Postgres | localhost:5432 |

O container da API aplica `alembic upgrade head` no entrypoint antes de servir, então o
banco já sobe migrado.

A chave da OpenAI é opcional. Sem ela a aplicação funciona por inteiro: a análise
determinística, o gerador e a conferência não dependem de IA, e o endpoint de revisão
responde `ai_available: false`.

---

## Como usar

1. Baixe a planilha de resultados da modalidade no portal de loterias da Caixa.
2. Abra o painel, escolha a modalidade e vá na aba **Importar**.
3. Envie o arquivo. A importação **substitui todo o histórico daquela modalidade**, e só
   daquela. As outras ficam intactas.
4. Vá na aba **Análise** para ver frequência, atraso, z-score, padrões, sequências e pares.
5. Na aba **Gerador**, escolha a quantidade de números, a quantidade de jogos, o perfil e,
   se quiser reprodutibilidade, uma seed. O custo é calculado ao vivo.
6. Clique em um jogo para abrir o detalhamento, que é buscado sob demanda.
7. Informe o concurso e registre os jogos. Depois de importar o concurso sorteado, use
   **Conferir pendentes**.

Para uma aposta que voce **ja pagou na loteria**, nao precisa passar pelo gerador: na aba
**Meus jogos** da modalidade existe o bloco **Registrar aposta ja feita**. Marque as dezenas
no volante ou cole os numeros em qualquer separador, informe o concurso, e pronto. O custo
sai da tabela oficial, mas da para sobrescrever se voce pagou outro valor. As apostas
manuais aparecem com a etiqueta `manual` e entram na conferencia junto com as geradas.
Errou a digitacao, o botao `remover` apaga a aposta.

---

## Modalidades

| Modalidade | Universo | Mín | Máx | Acertos base | Preço base | Campo extra |
|---|---|---|---|---|---|---|
| Mega-Sena | 1 a 60 | 6 | 20 | 6 | R$ 6,00 | nenhum |
| Lotofácil | 1 a 25 | 15 | 20 | 15 | R$ 3,50 | nenhum |
| Quina | 1 a 80 | 5 | 15 | 5 | R$ 3,00 | nenhum |
| Dia de Sorte | 1 a 31 | 7 | 15 | 7 | R$ 2,50 | mês da sorte, 1 a 12 |
| Super Sete | 7 colunas de 0 a 9 | 7 | 21 | 7 colunas | R$ 3,00 | 1 a 3 dígitos por coluna |

A Lotofácil da Independência é um concurso especial da própria Lotofácil: o histórico e as
regras são os mesmos, então ela entra em `LOTOFACIL`.

### Custo

- Modalidades de dezena: `custo = C(n_escolhidos, acertos_base) * preco_base`
- Super Sete: `custo = (produto das escolhas por coluna) * preco_base`

Tudo em `Decimal`, arredondado com `ROUND_HALF_UP` em duas casas. Uma Mega com 10 dezenas
são 210 jogos, ou seja R$ 1.260,00, e a tela avisa antes de você gerar. O parâmetro
`budget_limit` bloqueia o lote que estoura o orçamento.

O preço tem data de vigência: `price_at(data)` devolve o valor que valia naquele momento,
então uma aposta antiga pode ser reprecificada sem mexer na regra de negócio.

---

## O motor de análise

Tudo em `api/app/analytics/`, funções puras sobre arrays NumPy, sem banco e sem framework.

| Módulo | O que calcula |
|---|---|
| `frequency.py` | frequência absoluta e relativa, janelas de 25, 50, 100 e 200, z-score binomial, ranking |
| `delays.py` | atraso atual, médio, desvio, máximo, razão de atraso e série para o heatmap |
| `patterns.py` | soma, paridade, primos, amplitude, terminações, quadrantes, múltiplos, percentis e `fit_score` |
| `sequences.py` | consecutivos, progressões aritméticas, repetição do concurso anterior, espelhos, linhas cheias |
| `cooccurrence.py` | matriz de pares com lift, trincas, transição de Markov, pares que nunca saíram juntos |
| `history_index.py` | essa combinação já saiu, algum subconjunto já saiu, melhor correspondência histórica |
| `supersete.py` | frequência, atraso e z-score por coluna, matriz 7 x 10 |
| `scoring.py` | score composto por dezena, perfis de peso |
| `filters.py` | filtros rígidos aplicados ao candidato |
| `generator.py` | pipeline determinístico de geração |

### Z-score

Aproximação binomial sobre a janela: `esperado = W * p`, `desvio = sqrt(W * p * (1 - p))`,
`z = (observado - esperado) / desvio`, com `p = acertos_base / universo`. Acima de +1,5 a
dezena é classificada como quente, abaixo de -1,5 como fria.

### Razão de atraso

`delay_ratio = atraso_atual / max(atraso_medio, 1)`. Acima de 1,5 a dezena é marcada como
atrasada. O piso de 1 no denominador existe porque uma dezena que historicamente sai em
quase todo concurso tem atraso médio próximo de zero, e sem o piso qualquer ausência dela
ficaria com razão zero.

### Filtros por modalidade

Cada filtro e um teste de aprovado ou reprovado sobre o jogo, e **todos os limites saem do
proprio historico importado, por percentil**, nunca de numero chutado.

| Filtro | Mega | Lotofacil | Quina | Dia de Sorte | Super Sete |
|---|:--:|:--:|:--:|:--:|:--:|
| Numeros Pares e Impares | sim | sim | sim | sim | sim |
| Soma dos Numeros | sim | sim | sim | sim | sim |
| Dezenas por Linha | sim | sim | sim | sim | sim |
| Dezenas por Coluna | sim | sim | sim | sim | nao |
| Repetidas no Concurso Anterior | sim | sim | sim | sim | sim |
| Sequencia grande de Numeros | sim | sim | sim | sim | nao |
| Sequencia grande de Saltos | sim | sim | sim | sim | nao |
| Numeros de Fibonacci | sim | sim | sim | sim | sim |
| Numeros Primos | sim | sim | sim | sim | sim |
| Principio de Pareto | nao | sim | nao | nao | nao |
| Pesos | Inteligentes | Pesos | Inteligentes | Inteligentes | Inteligentes |

Definicoes que exigiram decisao:

- **Saltos**: o maior bloco de dezenas consecutivas do volante que o jogo deixou de fora.
  Um jogo `1 2 3 4 5 6` na Mega deixa um salto de 54.
- **Fibonacci**: os numeros da sequencia que cabem no universo. Na Mega sao nove:
  1, 2, 3, 5, 8, 13, 21, 34 e 55.
- **Linha e coluna**: a faixa sai do menor e do maior valor de cada concurso, e nao da
  distribuicao marginal, porque o teste precisa valer em todas as linhas ao mesmo tempo.
- **Pareto**: o volante e dividido em tantos blocos quanto a aposta base tem dezenas, e a
  dezena da posicao i precisa cair perto do bloco i. A regra foi reconstruida por ajuste
  contra um gabarito publicado de 100 concursos da Mega, onde ela aprova os 92 marcados
  como dentro do padrao. A folga acompanha o tamanho da aposta.
- **Pesos**: o peso medio das dezenas do jogo, na escala do score do perfil, dentro da
  faixa historica.

### Eficiencia dos filtros

`GET /api/modalities/{modality}/filters/efficiency` roda cada filtro contra os concursos que
realmente sairam e devolve quantos passariam. E a medida honesta de calibragem: um filtro
que reprova resultado real esta cortando jogo bom, e a tela mostra o percentual ao lado de
cada checkbox.

Medido sobre os ultimos 200 concursos reais: Mega 92,7% de eficiencia geral, Lotofacil
91,1%, Quina 94,6%, Dia de Sorte 92,5%.

### Combinacao ja sorteada

Por padrao a politica e `reject`: o jogo cuja combinacao ja saiu em algum concurso e
descartado e refeito, e nunca chega na resposta. Para volantes maiores que a aposta base a
verificacao olha tambem os subconjuntos.

### Perfis do gerador

| Perfil | freq | delay | markov | cooc | global |
|---|---|---|---|---|---|
| `balanced` | 0,25 | 0,25 | 0,15 | 0,15 | 0,20 |
| `hot` | 0,50 | 0,05 | 0,20 | 0,15 | 0,10 |
| `cold` | 0,05 | 0,55 | 0,10 | 0,10 | 0,20 |
| `pattern` | 0,15 | 0,15 | 0,20 | 0,40 | 0,10 |
| `uniform` | pesos zerados, amostragem uniforme, grupo de controle |

Os pesos podem ser sobrescritos por request. O componente de co-ocorrência é recalculado a
cada dezena adicionada ao jogo em construção, porque depende das que já foram escolhidas.

### Pipeline de geração

1. Calcula o score de cada dezena conforme o perfil.
2. Amostra sem reposição, ponderando pelo score, recalculando a co-ocorrência a cada dezena.
3. Aplica os filtros rígidos; candidato reprovado é descartado.
4. Rejeita candidato cuja interseção com qualquer jogo já aceito no lote passe de
   `max_overlap` (padrão `acertos_base - 2`), para não gastar orçamento com cinco jogos
   quase iguais.
5. Consulta o `history_index` e preenche `already_drawn` e `matched_contests`.
6. Gera um pool de cinco vezes o pedido e devolve os melhores por
   `engine_score = 0,6 * media_score_dezenas + 0,4 * fit_score`.
7. Estoura com erro claro se os filtros forem restritivos demais para a configuração pedida.

Mesma seed e mesmos parâmetros produzem exatamente os mesmos jogos.

---

## API

Prefixo `/api`. Todo erro sai em ProblemDetails, com `code`, `detail` e `request_id`.

```
GET    /health

POST   /modalities/{modality}/draws:import      multipart, substituição total
GET    /modalities/{modality}/draws             paginado, filtros de concurso e data
GET    /modalities/{modality}/draws/latest
GET    /modalities/{modality}/import-batches

GET    /modalities/{modality}/rules
GET    /modalities/{modality}/pricing/preview?n=7&games=5
GET    /modalities/{modality}/pricing/table

GET    /modalities/{modality}/analysis          snapshot completo, cacheado por hash do histórico
GET    /modalities/{modality}/analysis/numbers
GET    /modalities/{modality}/analysis/patterns
GET    /modalities/{modality}/analysis/pairs

POST   /modalities/{modality}/games:generate    resposta enxuta
GET    /game-batches
GET    /game-batches/{id}
POST   /game-batches/{id}/ai-review
GET    /games/{id}/insight                      detalhamento completo, sob demanda
POST   /games/{id}/ai-review

POST   /bets                                    a partir de game_id, ou manual com modality e numbers
GET    /bets
GET    /bets/{id}
DELETE /bets/{id}
POST   /bets:check
GET    /bets/summary
```

### Geração: request

```json
{
  "numbers_per_game": 7,
  "games": 5,
  "profile": "balanced",
  "seed": 42,
  "budget_limit": 300.00,
  "filters": { "enforce_sum": true, "max_consecutive": 2, "on_already_drawn": "flag" },
  "extras": { "month_strategy": "auto" }
}
```

### Geração: resposta

É isso e nada mais. Sem métricas por jogo, sem justificativa.

```json
{
  "batch_id": "uuid",
  "modality": "MEGA_SENA",
  "seed": 42,
  "games": [
    { "id": "uuid", "numbers": [4, 12, 23, 38, 47, 55, 58], "already_drawn": false, "extras": null }
  ],
  "cost": { "per_game": "42.00", "total": "210.00", "within_budget": true }
}
```

O detalhamento (soma, paridade, primos, quadrantes, dezenas quentes usadas, melhor
correspondência histórica) vive em `GET /games/{id}/insight` e só é calculado quando o
usuário abre o jogo na tela.

---

## Importação

`POST /api/modalities/{modality}/draws:import`, multipart, aceita `.xlsx` e `.csv`.

1. O arquivo inteiro é lido e validado em memória, antes de qualquer escrita.
2. São validados: concursos duplicados, quantidade de dezenas por linha, dezenas fora do
   universo, datas inválidas e campo extra ausente.
3. Falhando a validação, a resposta é `422` com a lista de erros por linha e **nada é
   apagado**.
4. Passando, uma única transação apaga os concursos daquela modalidade, insere em massa e
   grava o lote de importação.
5. O escopo do delete é apenas a modalidade enviada.
6. O `sha256` do arquivo é calculado e o resumo traz linhas importadas, faixa de concursos
   e período.
7. O snapshot de análise daquela modalidade é invalidado.

Os cabeçalhos são normalizados antes de serem resolvidos (sem acento, sem espaço, minúsculo),
porque a Caixa alterna entre `Data Sorteio` e `Data do Sorteio`, e cada modalidade usa
`Bola1..BolaN`, `Coluna1..Coluna7` ou `Mês da Sorte`. As colunas de premiação que vêm
depois das dezenas (ganhadores, rateio, cidade) são simplesmente ignoradas.

### Particularidades do arquivo oficial

Duas coisas nos arquivos publicados pela Caixa exigem tratamento, e as duas têm teste de
regressão em `tests/integration/test_parser.py`:

1. **A dimensão da aba vem declarada como uma única célula.** No modo `read_only` o openpyxl
   confia nessa declaração e para no cabeçalho, fazendo uma planilha com milhares de
   concursos chegar ao parser como se estivesse vazia. O parser chama `reset_dimensions()`
   para forçar a leitura real.
2. **O Dia de Sorte grava o mês com entidade HTML**, como `Mar&ccedil;o`. A normalização
   passa por `html.unescape` antes de tirar o acento.

---

## Camada de IA

A IA não gera números. Ela recebe estatísticas já calculadas e jogos já gerados, e produz
leitura do histórico e ranking. Isso elimina dezena inválida alucinada, reduz custo de token
e mantém o resultado reproduzível.

- Modelo configurável por `OPENAI_MODEL`, `temperature` 0.2.
- `response_format` com `json_schema` em modo estrito.
- Timeout de 30s e 2 tentativas com backoff.
- Se a resposta citar um id de jogo que não estava no lote, a resposta inteira é descartada.
- Degradação graciosa: qualquer falha devolve `ai_available: false` e a aplicação segue.

O system prompt fica em [`api/app/infrastructure/ai/prompts/analyst.md`](api/app/infrastructure/ai/prompts/analyst.md).

---

## Rodando no VS Code

Abra a pasta `lotto-lab` (a raiz, não `api` nem `web` separados). O projeto já vem com
`.vscode/` configurado: interpretador apontando para `api/.venv`, pytest descoberto pela
aba de testes, ruff formatando Python ao salvar, prettier e eslint no front.

Na primeira abertura o VS Code sugere as extensões recomendadas em
`.vscode/extensions.json`. Aceite: Python, Pylance, Ruff, Docker, ESLint, Prettier,
Tailwind e REST Client.

### Jeito 1: tudo em container

`Ctrl+Shift+B` roda a task **stack: subir tudo**, que é o `docker compose up -d`. Para
acompanhar o que a API está fazendo, rode a task **stack: logs da API**.

### Jeito 2: API com breakpoint

Para depurar o back de verdade, deixe só o banco em container e rode a API pelo VS Code:

1. Rode a task **db: subir Postgres**.
2. Se o container da API estiver de pé, pare ele, porque os dois disputam a porta 8000:
   `docker compose stop api`.
3. Vá em Run and Debug e escolha **API (uvicorn, com breakpoint)**. Essa configuração já
   aponta o `DATABASE_URL` para `localhost:5432` e liga `justMyCode: false`, então o
   breakpoint pega também dentro do pacote `analytics`.
4. Para o front, rode a task **front: dev server**.

A configuração composta **Stack local (API + Front)** sobe o banco, a API em modo debug e
abre o Chrome no painel de uma vez só.

### Testes

A aba Testing lista a suíte inteira e roda arquivo por arquivo. Para depurar um teste
específico, abra o arquivo e use a configuração **Testes: arquivo aberto**. Os testes de
integração precisam do Postgres no ar; sem ele, pulam sozinhos.

### Chamando a API sem sair do editor

`api/requests.http` tem as requisições prontas para a extensão REST Client, encadeadas:
a geração guarda a resposta e os blocos seguintes reaproveitam o `batch_id` e o `id` do
primeiro jogo.

---

## Desenvolvimento local

### Back

```bash
cd api
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

Testes, lint e tipos:

```bash
cd api && .venv/Scripts/python.exe -m pytest -q
```

```bash
cd api && .venv/Scripts/python.exe -m ruff check app tests
```

```bash
cd api && .venv/Scripts/python.exe -m mypy app
```

Os testes de integração precisam de um Postgres alcançável. Suba só o banco com:

```bash
docker compose up -d db
```

Sem banco, esses testes são pulados com a instrução na mensagem e o resto da suíte roda
normalmente. O banco de teste `lottolab_test` é criado sozinho e o esquema é montado pela
própria migration do Alembic, para que ela também seja exercitada.

### Front

```bash
cd web && npm install
```

```bash
cd web && npm run dev
```

```bash
cd web && npm run test && npm run lint && npm run build
```

### Nova migration

```bash
cd api && .venv/Scripts/python.exe -m alembic revision --autogenerate -m "descricao"
```

---

## Estrutura

```
lotto-lab/
├─ docker-compose.yml
├─ .env.example
├─ README.md
├─ api/
│  ├─ Dockerfile, entrypoint.sh, pyproject.toml, alembic.ini
│  ├─ alembic/versions/
│  ├─ app/
│  │  ├─ core/            config, Result, erros, handler global, log JSON
│  │  ├─ domain/          enums, entidades, regras das modalidades, precificação
│  │  ├─ application/     DTOs e casos de uso
│  │  ├─ analytics/       o motor, funções puras sobre NumPy
│  │  ├─ infrastructure/  banco, repositórios, parsers, IA
│  │  └─ interfaces/http/ roteadores
│  └─ tests/              domain, analytics, integration
└─ web/
   └─ src/
      ├─ app/             router, layout, providers
      ├─ config/          modalities.ts, espelho de MODALITY_RULES
      ├─ features/        dashboard, import, analysis, generator, bets
      └─ shared/          api, ui, hooks, lib
```

### Uma tela por modalidade, não cinco

O front tem uma única rota `/m/:modality`, dirigida por
[`web/src/config/modalities.ts`](web/src/config/modalities.ts). Volante, cores, limites e
campos extras saem dessa config. O Super Sete é a única exceção estrutural, porque o volante
dele é de colunas e não de dezenas: ele declara `boardKind: 'columns'` e recebe o próprio
componente de volante e o próprio painel de análise.

---

## Observabilidade

Log estruturado em JSON com `request_id` propagado por requisição, duração das operações de
análise e geração, e uso de token da IA. O `request_id` também volta no header
`x-request-id` e dentro do ProblemDetails, o que amarra o erro visto na tela ao log.
