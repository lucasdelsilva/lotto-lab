"""Co-ocorrencia entre dezenas, trincas frequentes e transicao de Markov."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np

from app.analytics.frequency import FloatArray, IntArray, indicator_matrix
from app.domain.rules import ModalityRule

TOP_TRIPLES = 50
TOP_PAIRS = 50


@dataclass(frozen=True, slots=True)
class CooccurrenceReport:
    counts: IntArray
    lift: FloatArray
    rule: ModalityRule

    def number_at(self, index: int) -> int:
        return index + self.rule.universe_min

    def top_pairs(self, limit: int = TOP_PAIRS) -> list[dict[str, Any]]:
        size = self.counts.shape[0]
        rows, cols = np.triu_indices(size, k=1)
        order = np.argsort(-self.counts[rows, cols], kind="stable")[:limit]
        return [
            {
                "pair": [self.number_at(int(rows[index])), self.number_at(int(cols[index]))],
                "count": int(self.counts[rows[index], cols[index]]),
                "lift": round(float(self.lift[rows[index], cols[index]]), 4),
            }
            for index in order
        ]

    def never_together(self, limit: int = 200) -> list[list[int]]:
        size = self.counts.shape[0]
        rows, cols = np.triu_indices(size, k=1)
        zeros = np.flatnonzero(self.counts[rows, cols] == 0)[:limit]
        return [
            [self.number_at(int(rows[index])), self.number_at(int(cols[index]))]
            for index in zeros
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "top_pairs": self.top_pairs(),
            "never_together": self.never_together(),
        }


def pair_counts(draws: IntArray, rule: ModalityRule) -> IntArray:
    """Matriz universo x universo com a contagem de concursos em que o par saiu junto.

    A diagonal guarda a frequencia individual da dezena.
    """
    if draws.shape[0] == 0:
        return np.zeros((rule.universe_size, rule.universe_size), dtype=np.int64)
    indicators = indicator_matrix(draws, rule).astype(np.int64)
    return indicators.T @ indicators


def pair_lift(counts: IntArray, total_draws: int) -> FloatArray:
    """lift(a, b) = P(a e b) / (P(a) * P(b)).

    Acima de 1 significa que o par apareceu junto mais do que o acaso sugeriria no
    historico observado. Nao e previsao, e descricao do passado.
    """
    size = counts.shape[0]
    if total_draws == 0:
        return np.zeros((size, size), dtype=np.float64)
    individual = np.diag(counts).astype(np.float64) / total_draws
    joint = counts.astype(np.float64) / total_draws
    denominator = np.outer(individual, individual)
    with np.errstate(divide="ignore", invalid="ignore"):
        lift = np.where(denominator > 0, joint / denominator, 0.0)
    np.fill_diagonal(lift, 0.0)
    return np.nan_to_num(lift, nan=0.0, posinf=0.0)


def cooccurrence_report(draws: IntArray, rule: ModalityRule) -> CooccurrenceReport:
    counts = pair_counts(draws, rule)
    return CooccurrenceReport(
        counts=counts, lift=pair_lift(counts, draws.shape[0]), rule=rule
    )


def top_triples(draws: IntArray, limit: int = TOP_TRIPLES) -> list[dict[str, Any]]:
    """Trincas mais frequentes do historico."""
    counter: Counter[tuple[int, int, int]] = Counter()
    for row in draws:
        for triple in combinations(sorted(int(value) for value in row), 3):
            counter[triple] += 1
    return [
        {"triple": list(triple), "count": count} for triple, count in counter.most_common(limit)
    ]


def markov_transition(draws: IntArray, rule: ModalityRule) -> FloatArray:
    """Matriz de transicao de 1a ordem: P(dezena b sair em t+1 | dezena a saiu em t)."""
    size = rule.universe_size
    if draws.shape[0] < 2:
        return np.zeros((size, size), dtype=np.float64)
    indicators = indicator_matrix(draws, rule).astype(np.float64)
    current, following = indicators[:-1], indicators[1:]
    joint = current.T @ following
    origin_counts = current.sum(axis=0).reshape(-1, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        transition = np.where(origin_counts > 0, joint / origin_counts, 0.0)
    return np.nan_to_num(transition, nan=0.0, posinf=0.0)


def next_draw_probability(
    transition: FloatArray, last_draw: IntArray, rule: ModalityRule
) -> FloatArray:
    """Probabilidade media de cada dezena no proximo concurso, dado o ultimo resultado."""
    size = rule.universe_size
    if last_draw.size == 0:
        return np.zeros(size, dtype=np.float64)
    indices = np.asarray(last_draw, dtype=np.int64) - rule.universe_min
    return transition[indices].mean(axis=0)


def average_lift_with(lift: FloatArray, selected: list[int], rule: ModalityRule) -> FloatArray:
    """Lift medio de cada dezena em relacao as dezenas ja escolhidas no jogo em construcao.

    E o componente do score que muda a cada dezena adicionada, por isso precisa ser
    recalculado dentro do laco do gerador.
    """
    size = rule.universe_size
    if not selected:
        return np.zeros(size, dtype=np.float64)
    indices = [value - rule.universe_min for value in selected]
    return lift[:, indices].mean(axis=1)
