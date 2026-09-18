"""Filtros rigidos aplicados ao jogo candidato.

Cada filtro e um teste de aprovado ou reprovado sobre um jogo, e todos os limites saem do
proprio historico importado, por percentil, nunca de numero chutado. Isso permite medir a
eficiencia de cada filtro: rodar o filtro contra os concursos que realmente sairam e ver
quantos deles passariam. Um filtro que reprova metade dos concursos reais e um filtro mal
calibrado, e a tela mostra isso.

O catalogo de filtros varia por modalidade, porque nem todo criterio faz sentido em todo
volante: o Super Sete nao tem coluna de dezenas, e o Principio de Pareto so foi definido
para a Lotofacil.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.analytics.frequency import IntArray
from app.analytics.patterns import PRIMES, describe_game, quadrant_counts
from app.analytics.sequences import max_consecutive_run, repeat_from_previous
from app.domain.enums import AlreadyDrawnPolicy, FilterId, Modality
from app.domain.rules import ModalityRule

# Percentis usados para montar a faixa aceita de cada metrica.
BAND_LOW = 10
BAND_HIGH = 90

# Linha e coluna sao testadas em conjunto: basta uma fora da faixa para reprovar o jogo.
# Por isso a faixa delas nao pode sair da distribuicao marginal, e sim do minimo e do
# maximo observados em cada concurso, senao o filtro reprova ate resultado que saiu.
JOINT_BAND_ALPHA = 5

# Pareto: a documentacao descreve o criterio como uma faixa diagonal. O volante e dividido
# em tantos blocos quanto a aposta base tem dezenas, e a dezena da posicao i do jogo
# ordenado precisa cair no bloco i, aceitando um bloco de folga para cada lado.
# Reconstruido por ajuste contra um gabarito publicado de 100 concursos da Mega, onde esta
# regra reprova os oito jogos marcados como fora do padrao.
PARETO_TOLERANCE = 1
# Quantas dezenas podem ficar fora da diagonal. Precisa acompanhar o tamanho da aposta:
# na Mega sao 6 dezenas em 60 e cada bloco tem 10 numeros, mas na Lotofacil sao 15 em 25 e
# o bloco cai para menos de dois numeros, o que tornaria a diagonal impossivel de cumprir.
PARETO_MAX_OUT_RATIO = 1 / 3
PARETO_MIN_OUT = 2

# A faixa observada de cada posicao nao entra na decisao do filtro, que usa os blocos, mas
# continua calculada porque a tela mostra ela junto do jogo.
PARETO_LOW = 3
PARETO_HIGH = 97


@dataclass(frozen=True, slots=True)
class FilterDefinition:
    id: FilterId
    label: str
    description: str


FILTER_DEFINITIONS: dict[FilterId, FilterDefinition] = {
    FilterId.EVEN_ODD: FilterDefinition(
        FilterId.EVEN_ODD,
        "Numeros Pares e Impares",
        "A quantidade de pares do jogo precisa cair na faixa que o historico mostra.",
    ),
    FilterId.SUM: FilterDefinition(
        FilterId.SUM,
        "Soma dos Numeros",
        "A soma das dezenas precisa cair na faixa historica, nem concentrada no inicio "
        "nem no fim do volante.",
    ),
    FilterId.ROWS: FilterDefinition(
        FilterId.ROWS,
        "Dezenas por Linha",
        "Nenhuma linha do volante pode concentrar ou ficar sem dezenas fora do padrao "
        "historico.",
    ),
    FilterId.COLUMNS: FilterDefinition(
        FilterId.COLUMNS,
        "Dezenas por Coluna",
        "Mesma ideia da linha, aplicada as colunas do volante.",
    ),
    FilterId.REPEATED: FilterDefinition(
        FilterId.REPEATED,
        "Repetidas no Concurso Anterior",
        "Quantas dezenas do jogo ja estavam no ultimo concurso, dentro da faixa historica.",
    ),
    FilterId.CONSECUTIVE: FilterDefinition(
        FilterId.CONSECUTIVE,
        "Sequencia grande de Numeros",
        "Corta jogos com uma corrida longa de dezenas seguidas, tipo 10 11 12 13.",
    ),
    FilterId.GAPS: FilterDefinition(
        FilterId.GAPS,
        "Sequencia grande de Saltos",
        "Corta jogos que deixam um bloco longo do volante sem nenhuma dezena marcada.",
    ),
    FilterId.FIBONACCI: FilterDefinition(
        FilterId.FIBONACCI,
        "Numeros de Fibonacci",
        "Quantidade de dezenas de Fibonacci dentro da faixa historica.",
    ),
    FilterId.PRIMES: FilterDefinition(
        FilterId.PRIMES,
        "Numeros Primos",
        "Quantidade de dezenas primas dentro da faixa historica.",
    ),
    FilterId.PARETO: FilterDefinition(
        FilterId.PARETO,
        "Principio de Pareto",
        "Cada dezena precisa estar no bloco do volante que costuma ocupar aquela posicao "
        "do jogo ordenado.",
    ),
    FilterId.WEIGHTS: FilterDefinition(
        FilterId.WEIGHTS,
        "Pesos Inteligentes",
        "O peso medio das dezenas do jogo, calculado pelo score do perfil, precisa cair "
        "na faixa historica.",
    ),
}

# Quais filtros existem em cada modalidade.
FILTER_CATALOG: dict[Modality, tuple[FilterId, ...]] = {
    Modality.LOTOFACIL: (
        FilterId.EVEN_ODD,
        FilterId.SUM,
        FilterId.ROWS,
        FilterId.COLUMNS,
        FilterId.REPEATED,
        FilterId.CONSECUTIVE,
        FilterId.GAPS,
        FilterId.FIBONACCI,
        FilterId.PRIMES,
        FilterId.PARETO,
        FilterId.WEIGHTS,
    ),
    Modality.MEGA_SENA: (
        FilterId.EVEN_ODD,
        FilterId.SUM,
        FilterId.ROWS,
        FilterId.COLUMNS,
        FilterId.REPEATED,
        FilterId.CONSECUTIVE,
        FilterId.GAPS,
        FilterId.FIBONACCI,
        FilterId.PRIMES,
        FilterId.WEIGHTS,
    ),
    Modality.QUINA: (
        FilterId.EVEN_ODD,
        FilterId.SUM,
        FilterId.ROWS,
        FilterId.COLUMNS,
        FilterId.REPEATED,
        FilterId.CONSECUTIVE,
        FilterId.GAPS,
        FilterId.FIBONACCI,
        FilterId.PRIMES,
        FilterId.WEIGHTS,
    ),
    Modality.DIA_DE_SORTE: (
        FilterId.EVEN_ODD,
        FilterId.SUM,
        FilterId.ROWS,
        FilterId.COLUMNS,
        FilterId.REPEATED,
        FilterId.CONSECUTIVE,
        FilterId.GAPS,
        FilterId.FIBONACCI,
        FilterId.PRIMES,
        FilterId.WEIGHTS,
    ),
    Modality.SUPER_SETE: (
        FilterId.EVEN_ODD,
        FilterId.SUM,
        FilterId.ROWS,
        FilterId.REPEATED,
        FilterId.FIBONACCI,
        FilterId.PRIMES,
        FilterId.WEIGHTS,
    ),
}

# A Lotofacil chama o filtro de peso apenas de "Pesos"; as demais, de "Pesos Inteligentes".
FILTER_LABEL_OVERRIDES: dict[tuple[Modality, FilterId], str] = {
    (Modality.LOTOFACIL, FilterId.WEIGHTS): "Pesos",
    (Modality.SUPER_SETE, FilterId.ROWS): "Numeros por Linha",
}


def catalog_for(modality: Modality) -> list[dict[str, Any]]:
    """Catalogo pronto para o front montar os checkboxes da modalidade."""
    rows = []
    for filter_id in FILTER_CATALOG[modality]:
        definition = FILTER_DEFINITIONS[filter_id]
        rows.append(
            {
                "id": filter_id.value,
                "label": FILTER_LABEL_OVERRIDES.get((modality, filter_id), definition.label),
                "description": definition.description,
                "default_enabled": True,
            }
        )
    return rows


def fibonacci_within(rule: ModalityRule) -> frozenset[int]:
    """Numeros de Fibonacci que cabem no universo da modalidade."""
    values: set[int] = set()
    a, b = 1, 2
    while a <= rule.universe_max:
        if a >= rule.universe_min:
            values.add(a)
        a, b = b, a + b
    if rule.universe_min <= 1:
        values.add(1)
    return frozenset(values)


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Quais filtros estao ligados. Um id ausente do conjunto esta desligado."""

    enabled: frozenset[FilterId] = field(default_factory=lambda: frozenset(FilterId))
    on_already_drawn: AlreadyDrawnPolicy = AlreadyDrawnPolicy.REJECT
    max_consecutive: int | None = None
    min_quadrants_covered: int = 0

    def is_on(self, filter_id: FilterId) -> bool:
        return filter_id in self.enabled

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": sorted(item.value for item in self.enabled),
            "on_already_drawn": self.on_already_drawn.value,
            "max_consecutive": self.max_consecutive,
            "min_quadrants_covered": self.min_quadrants_covered,
        }

    @classmethod
    def for_modality(cls, modality: Modality, enabled: Sequence[str] | None = None) -> FilterConfig:
        disponiveis = set(FILTER_CATALOG[modality])
        if enabled is None:
            ativos = frozenset(disponiveis)
        else:
            ativos = frozenset(
                FilterId(item) for item in enabled if FilterId(item) in disponiveis
            )
        return cls(enabled=ativos)


def pareto_block(number: int, rule: ModalityRule) -> int:
    """Bloco do volante em que a dezena cai, com um bloco por posicao da aposta base."""
    tamanho = rule.universe_size / rule.base_hits
    indice = int((number - rule.universe_min) // tamanho) + 1
    return min(rule.base_hits, max(1, indice))


def largest_gap(numbers: Sequence[int], rule: ModalityRule) -> int:
    """Maior bloco de dezenas consecutivas do volante que o jogo deixou de fora."""
    marcadas = set(numbers)
    maior = atual = 0
    for value in rule.universe():
        if value in marcadas:
            atual = 0
        else:
            atual += 1
            maior = max(maior, atual)
    return maior


def row_counts(numbers: Sequence[int], rule: ModalityRule) -> list[int]:
    if rule.board is None:
        return []
    counts = [0] * rule.board.rows
    for value in numbers:
        counts[rule.board.position(value, rule.universe_min)[0]] += 1
    return counts


def column_counts(numbers: Sequence[int], rule: ModalityRule) -> list[int]:
    if rule.board is None:
        return []
    counts = [0] * rule.board.cols
    for value in numbers:
        counts[rule.board.position(value, rule.universe_min)[1]] += 1
    return counts


@dataclass(frozen=True, slots=True)
class HistoricalBounds:
    """Todos os limites que os filtros consultam, calculados uma vez por historico."""

    rule: ModalityRule
    even: tuple[float, float]
    total_sum: tuple[float, float]
    row_count: tuple[float, float]
    column_count: tuple[float, float]
    repeated: tuple[float, float]
    consecutive_max: float
    gap_max: float
    fibonacci: tuple[float, float]
    primes: tuple[float, float]
    pareto_bands: tuple[tuple[float, float], ...]
    weight: tuple[float, float]
    last_draw: tuple[int, ...]
    fibonacci_set: frozenset[int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "even": list(self.even),
            "sum": list(self.total_sum),
            "row_count": list(self.row_count),
            "column_count": list(self.column_count),
            "repeated": list(self.repeated),
            "consecutive_max": self.consecutive_max,
            "gap_max": self.gap_max,
            "fibonacci": list(self.fibonacci),
            "primes": list(self.primes),
            "pareto_bands": [list(band) for band in self.pareto_bands],
            "weight": list(self.weight),
            "fibonacci_numbers": sorted(self.fibonacci_set),
        }


def _band(
    values: Sequence[float] | np.ndarray, low: int = BAND_LOW, high: int = BAND_HIGH
) -> tuple[float, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return (0.0, 0.0)
    return (float(np.percentile(array, low)), float(np.percentile(array, high)))


def _joint_band(per_draw: IntArray) -> tuple[float, float]:
    """Faixa para um teste que precisa valer em todas as posicoes ao mesmo tempo.

    Calibra sobre o menor e o maior valor de cada concurso, e nao sobre todos os valores
    juntos, para que a taxa de aprovacao do jogo inteiro fique na meta.
    """
    if per_draw.size == 0:
        return (0.0, 0.0)
    minimos = per_draw.min(axis=1)
    maximos = per_draw.max(axis=1)
    return (
        float(np.percentile(minimos, JOINT_BAND_ALPHA)),
        float(np.percentile(maximos, 100 - JOINT_BAND_ALPHA)),
    )


def build_bounds(
    draws: IntArray, rule: ModalityRule, number_scores: np.ndarray | None = None
) -> HistoricalBounds:
    """Calcula todos os limites a partir do historico, por percentil."""
    fib = fibonacci_within(rule)
    vazio = (0.0, 0.0)

    if draws.shape[0] == 0:
        return HistoricalBounds(
            rule=rule,
            even=vazio,
            total_sum=vazio,
            row_count=vazio,
            column_count=vazio,
            repeated=vazio,
            consecutive_max=float(rule.base_hits),
            gap_max=float(rule.universe_size),
            fibonacci=vazio,
            primes=vazio,
            pareto_bands=(),
            weight=vazio,
            last_draw=(),
            fibonacci_set=fib,
        )

    evens = np.count_nonzero(draws % 2 == 0, axis=1)
    sums = draws.sum(axis=1)

    prime_mask = np.zeros(rule.universe_max + 1, dtype=bool)
    for prime in PRIMES:
        if prime <= rule.universe_max:
            prime_mask[prime] = True
    primes = prime_mask[draws].sum(axis=1)

    fib_mask = np.zeros(rule.universe_max + 1, dtype=bool)
    for value in fib:
        fib_mask[value] = True
    fibs = fib_mask[draws].sum(axis=1)

    consecutives = np.array([max_consecutive_run(row.tolist()) for row in draws], dtype=np.int64)
    gaps = np.array([largest_gap(row.tolist(), rule) for row in draws], dtype=np.int64)

    repeats = np.array(
        [repeat_from_previous(draws[i], draws[i - 1]) for i in range(1, draws.shape[0])],
        dtype=np.int64,
    )

    if rule.board is not None:
        linhas = np.array([row_counts(row.tolist(), rule) for row in draws], dtype=np.int64)
        colunas = np.array([column_counts(row.tolist(), rule) for row in draws], dtype=np.int64)
        faixa_linha = _joint_band(linhas)
        faixa_coluna = _joint_band(colunas)
    else:
        faixa_linha = faixa_coluna = vazio

    ordenados = np.sort(draws, axis=1)
    bandas = tuple(
        (
            float(np.percentile(ordenados[:, i], PARETO_LOW)),
            float(np.percentile(ordenados[:, i], PARETO_HIGH)),
        )
        for i in range(ordenados.shape[1])
    )

    if number_scores is not None and number_scores.size:
        indices = draws - rule.universe_min
        pesos = number_scores[indices].mean(axis=1)
        faixa_peso = _band(pesos)
    else:
        faixa_peso = vazio

    return HistoricalBounds(
        rule=rule,
        even=_band(evens),
        total_sum=_band(sums),
        row_count=faixa_linha,
        column_count=faixa_coluna,
        repeated=_band(repeats) if repeats.size else vazio,
        consecutive_max=float(np.percentile(consecutives, BAND_HIGH)),
        gap_max=float(np.percentile(gaps, BAND_HIGH)),
        fibonacci=_band(fibs),
        primes=_band(primes),
        pareto_bands=bandas,
        weight=faixa_peso,
        last_draw=tuple(int(value) for value in draws[-1]),
        fibonacci_set=fib,
    )


@dataclass(slots=True)
class FilterOutcome:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    failed: list[FilterId] = field(default_factory=list)


def check_filter(
    filter_id: FilterId,
    numbers: Sequence[int],
    rule: ModalityRule,
    config: FilterConfig,
    bounds: HistoricalBounds,
    scores: np.ndarray | None,
) -> str | None:
    """Devolve o motivo da reprovacao, ou None quando o jogo passa nesse filtro."""
    ordenados = sorted(numbers)

    if filter_id is FilterId.EVEN_ODD:
        pares = sum(1 for n in ordenados if n % 2 == 0)
        low, high = bounds.even
        if not low <= pares <= high:
            return f"{pares} pares fora da faixa historica {low:.0f} a {high:.0f}"

    elif filter_id is FilterId.SUM:
        total = sum(ordenados)
        low, high = bounds.total_sum
        if not low <= total <= high:
            return f"soma {total} fora da faixa historica {low:.0f} a {high:.0f}"

    elif filter_id is FilterId.ROWS and rule.board is not None:
        low, high = bounds.row_count
        counts = row_counts(ordenados, rule)
        for indice, quantidade in enumerate(counts, start=1):
            if not low <= quantidade <= high:
                return (
                    f"linha {indice} com {quantidade} dezenas, fora da faixa "
                    f"{low:.0f} a {high:.0f}"
                )

    elif filter_id is FilterId.COLUMNS and rule.board is not None:
        low, high = bounds.column_count
        counts = column_counts(ordenados, rule)
        for indice, quantidade in enumerate(counts, start=1):
            if not low <= quantidade <= high:
                return (
                    f"coluna {indice} com {quantidade} dezenas, fora da faixa "
                    f"{low:.0f} a {high:.0f}"
                )

    elif filter_id is FilterId.REPEATED and bounds.last_draw:
        repetidas = repeat_from_previous(ordenados, bounds.last_draw)
        low, high = bounds.repeated
        if not low <= repetidas <= high:
            return (
                f"{repetidas} dezenas repetidas do ultimo concurso, fora da faixa "
                f"{low:.0f} a {high:.0f}"
            )

    elif filter_id is FilterId.CONSECUTIVE:
        teto = (
            config.max_consecutive
            if config.max_consecutive is not None
            else bounds.consecutive_max
        )
        corrida = max_consecutive_run(ordenados)
        if corrida > teto:
            return f"sequencia de {corrida} dezenas seguidas, acima do limite {teto:.0f}"

    elif filter_id is FilterId.GAPS:
        salto = largest_gap(ordenados, rule)
        if salto > bounds.gap_max:
            return f"salto de {salto} dezenas sem marcacao, acima do limite {bounds.gap_max:.0f}"

    elif filter_id is FilterId.FIBONACCI:
        quantidade = sum(1 for n in ordenados if n in bounds.fibonacci_set)
        low, high = bounds.fibonacci
        if not low <= quantidade <= high:
            return f"{quantidade} numeros de Fibonacci fora da faixa {low:.0f} a {high:.0f}"

    elif filter_id is FilterId.PRIMES:
        quantidade = sum(1 for n in ordenados if n in PRIMES)
        low, high = bounds.primes
        if not low <= quantidade <= high:
            return f"{quantidade} primos fora da faixa historica {low:.0f} a {high:.0f}"

    elif filter_id is FilterId.PARETO:
        # So vale para o volante do tamanho da aposta base: com mais dezenas, a posicao de
        # cada uma deixa de corresponder a um bloco do volante.
        if len(ordenados) == rule.base_hits:
            fora = [
                (posicao, valor, pareto_block(valor, rule))
                for posicao, valor in enumerate(ordenados, start=1)
                if abs(pareto_block(valor, rule) - posicao) > PARETO_TOLERANCE
            ]
            limite = max(PARETO_MIN_OUT, round(rule.base_hits * PARETO_MAX_OUT_RATIO))
            if len(fora) > limite:
                posicao, valor, bloco = fora[0]
                return (
                    f"Pareto: {len(fora)} dezenas fora da faixa diagonal, a primeira e a "
                    f"dezena {valor} na posicao {posicao}, que cai no bloco {bloco}"
                )

    elif filter_id is FilterId.WEIGHTS and scores is not None and scores.size:
        low, high = bounds.weight
        if high > low:
            indices = [n - rule.universe_min for n in ordenados]
            peso = float(scores[indices].mean())
            if not low <= peso <= high:
                return f"peso medio {peso:.3f} fora da faixa historica {low:.3f} a {high:.3f}"

    return None


def evaluate(
    numbers: Sequence[int],
    rule: ModalityRule,
    config: FilterConfig,
    bounds: HistoricalBounds,
    scores: np.ndarray | None = None,
) -> FilterOutcome:
    """Roda todos os filtros ligados e para no primeiro que reprovar."""
    outcome = FilterOutcome(accepted=True)
    for filter_id in FILTER_CATALOG[rule.modality]:
        if not config.is_on(filter_id):
            continue
        motivo = check_filter(filter_id, numbers, rule, config, bounds, scores)
        if motivo is not None:
            outcome.accepted = False
            outcome.reasons.append(motivo)
            outcome.failed.append(filter_id)
            break

    if outcome.accepted and config.min_quadrants_covered and rule.board is not None:
        cobertos = sum(1 for count in quadrant_counts(numbers, rule) if count > 0)
        exigido = min(config.min_quadrants_covered, len(numbers))
        if cobertos < exigido:
            outcome.accepted = False
            outcome.reasons.append(
                f"cobertura de {cobertos} quadrantes abaixo do minimo {exigido}"
            )

    return outcome


def filter_efficiency(
    draws: IntArray,
    rule: ModalityRule,
    bounds: HistoricalBounds,
    scores: np.ndarray | None = None,
    sample: int = 100,
) -> list[dict[str, Any]]:
    """Quantos dos ultimos concursos reais passariam em cada filtro.

    E a medida honesta de calibragem: se um filtro reprova muitos resultados que de fato
    sairam, ele esta cortando jogo bom e deve ser desligado.
    """
    if draws.shape[0] == 0:
        return []

    janela = draws[-min(sample, draws.shape[0]) :]
    config = FilterConfig.for_modality(rule.modality)
    linhas = []
    for filter_id in FILTER_CATALOG[rule.modality]:
        aprovados = sum(
            1
            for row in janela
            if check_filter(filter_id, row.tolist(), rule, config, bounds, scores) is None
        )
        definicao = FILTER_DEFINITIONS[filter_id]
        linhas.append(
            {
                "id": filter_id.value,
                "label": FILTER_LABEL_OVERRIDES.get((rule.modality, filter_id), definicao.label),
                "approved": aprovados,
                "total": int(janela.shape[0]),
                "efficiency": round(aprovados / janela.shape[0], 4),
            }
        )
    return linhas


def describe_for_ui(numbers: Sequence[int], rule: ModalityRule) -> dict[str, Any]:
    """Metricas do jogo com os mesmos nomes que a tela dos filtros usa."""
    metrics = describe_game(numbers, rule)
    return metrics.as_dict() | {
        "rows": row_counts(numbers, rule),
        "columns": column_counts(numbers, rule),
        "largest_gap": largest_gap(numbers, rule),
        "fibonacci": sum(1 for n in numbers if n in fibonacci_within(rule)),
    }
