"""Padroes estruturais de um jogo e as faixas historicas de cada metrica."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from app.analytics.frequency import IntArray
from app.analytics.sequences import consecutive_pairs, max_consecutive_run
from app.domain.entities import GameMetrics
from app.domain.rules import ModalityRule

PERCENTILES: tuple[int, ...] = (10, 25, 50, 75, 90)

# Metricas comparadas contra a faixa historica no fit_score.
RANGED_METRICS: tuple[str, ...] = (
    "sum",
    "even",
    "primes",
    "spread",
    "max_consecutive",
    "multiples_of_3",
    "multiples_of_5",
)

_PRIME_LIMIT = 100


def _sieve(limit: int) -> frozenset[int]:
    flags = np.ones(limit + 1, dtype=bool)
    flags[:2] = False
    for candidate in range(2, int(limit**0.5) + 1):
        if flags[candidate]:
            flags[candidate * candidate :: candidate] = False
    return frozenset(int(value) for value in np.flatnonzero(flags))


PRIMES: frozenset[int] = _sieve(_PRIME_LIMIT)


def quadrant_counts(numbers: Sequence[int], rule: ModalityRule) -> tuple[int, ...]:
    """Quantas dezenas caem em cada um dos quatro quadrantes do volante."""
    if rule.board is None:
        return ()
    counts = [0, 0, 0, 0]
    for value in numbers:
        counts[rule.board.quadrant(value, rule.universe_min)] += 1
    return tuple(counts)


def ending_counts(numbers: Sequence[int]) -> dict[int, int]:
    """Contagem por terminacao, do digito final 0 ao 9."""
    counts = dict.fromkeys(range(10), 0)
    for value in numbers:
        counts[value % 10] += 1
    return counts


def describe_game(numbers: Sequence[int], rule: ModalityRule) -> GameMetrics:
    """Metricas completas de um unico jogo."""
    values = sorted(numbers)
    array = np.asarray(values, dtype=np.int64)
    even = int(np.count_nonzero(array % 2 == 0))
    return GameMetrics(
        total_sum=int(array.sum()),
        even_count=even,
        odd_count=len(values) - even,
        prime_count=sum(1 for value in values if value in PRIMES),
        spread=int(array.max() - array.min()) if array.size else 0,
        max_consecutive=max_consecutive_run(values),
        consecutive_pairs=consecutive_pairs(values),
        quadrants=quadrant_counts(values, rule),
        endings=ending_counts(values),
        multiples_of_3=int(np.count_nonzero(array % 3 == 0)),
        multiples_of_5=int(np.count_nonzero(array % 5 == 0)),
        mean=round(float(array.mean()), 3) if array.size else 0.0,
        median=round(float(np.median(array)), 3) if array.size else 0.0,
    )


def historical_metrics(draws: IntArray, rule: ModalityRule) -> dict[str, IntArray]:
    """Calcula as metricas de cada concurso do historico, coluna a coluna."""
    if draws.shape[0] == 0:
        empty = np.zeros(0, dtype=np.int64)
        return dict.fromkeys(RANGED_METRICS, empty) | {"repeat_from_previous": empty}

    sums = draws.sum(axis=1).astype(np.int64)
    evens = np.count_nonzero(draws % 2 == 0, axis=1).astype(np.int64)
    spreads = (draws.max(axis=1) - draws.min(axis=1)).astype(np.int64)
    multiples_3 = np.count_nonzero(draws % 3 == 0, axis=1).astype(np.int64)
    multiples_5 = np.count_nonzero(draws % 5 == 0, axis=1).astype(np.int64)

    prime_mask = np.zeros(rule.universe_max + 1, dtype=bool)
    for prime in PRIMES:
        if prime <= rule.universe_max:
            prime_mask[prime] = True
    primes = prime_mask[draws].sum(axis=1).astype(np.int64)

    consecutives = np.array(
        [max_consecutive_run(row.tolist()) for row in draws], dtype=np.int64
    )

    return {
        "sum": sums,
        "even": evens,
        "primes": primes,
        "spread": spreads,
        "max_consecutive": consecutives,
        "multiples_of_3": multiples_3,
        "multiples_of_5": multiples_5,
    }


def percentile_ranges(series: dict[str, IntArray]) -> dict[str, dict[str, float]]:
    """Percentis P10, P25, P50, P75 e P90 de cada metrica historica."""
    ranges: dict[str, dict[str, float]] = {}
    for name, values in series.items():
        if values.size == 0:
            ranges[name] = {f"p{p}": 0.0 for p in PERCENTILES}
            continue
        ranges[name] = {
            f"p{p}": round(float(np.percentile(values, p)), 3) for p in PERCENTILES
        }
        ranges[name]["min"] = float(values.min())
        ranges[name]["max"] = float(values.max())
        ranges[name]["mean"] = round(float(values.mean()), 3)
    return ranges


def metrics_to_series_names(metrics: GameMetrics) -> dict[str, float]:
    """Traduz as metricas de um jogo para as mesmas chaves das faixas historicas."""
    return {
        "sum": float(metrics.total_sum),
        "even": float(metrics.even_count),
        "primes": float(metrics.prime_count),
        "spread": float(metrics.spread),
        "max_consecutive": float(metrics.max_consecutive),
        "multiples_of_3": float(metrics.multiples_of_3),
        "multiples_of_5": float(metrics.multiples_of_5),
    }


def fit_score(metrics: GameMetrics, ranges: dict[str, dict[str, float]]) -> float:
    """Quanto o jogo esta dentro das faixas historicas, de 0 a 1.

    Cada metrica dentro do intervalo P10 a P90 nao sofre penalidade. Fora do intervalo, a
    penalidade cresce proporcionalmente a distancia, normalizada pela propria largura do
    intervalo, e satura em 1 para aquela metrica.
    """
    values = metrics_to_series_names(metrics)
    considered = [name for name in RANGED_METRICS if name in ranges and name in values]
    if not considered:
        return 1.0

    penalties = []
    for name in considered:
        low = ranges[name]["p10"]
        high = ranges[name]["p90"]
        width = high - low
        value = values[name]
        if low <= value <= high:
            penalties.append(0.0)
            continue
        distance = low - value if value < low else value - high
        reference = width if width > 0 else max(abs(low), 1.0)
        penalties.append(min(1.0, distance / reference))

    return round(max(0.0, 1.0 - float(np.mean(penalties))), 4)


def pattern_report(draws: IntArray, rule: ModalityRule) -> dict[str, Any]:
    """Faixas historicas mais os histogramas que o painel desenha."""
    series = historical_metrics(draws, rule)
    ranges = percentile_ranges(series)

    quadrants = np.zeros(4, dtype=np.int64)
    endings = np.zeros(10, dtype=np.int64)
    if draws.shape[0] and rule.board is not None:
        for row in draws:
            for index, count in enumerate(quadrant_counts(row.tolist(), rule)):
                quadrants[index] += count
    if draws.shape[0]:
        endings = np.bincount(draws.ravel() % 10, minlength=10).astype(np.int64)

    def histogram(values: IntArray, bins: int = 30) -> list[dict[str, float]]:
        if values.size == 0:
            return []
        counts, edges = np.histogram(values, bins=min(bins, max(1, int(np.ptp(values)) + 1)))
        return [
            {
                "start": round(float(edges[index]), 2),
                "end": round(float(edges[index + 1]), 2),
                "count": int(count),
            }
            for index, count in enumerate(counts)
        ]

    even_counts = series["even"]
    return {
        "ranges": ranges,
        "sum_histogram": histogram(series["sum"]),
        "even_distribution": [
            {"even": int(value), "count": int(count)}
            for value, count in enumerate(np.bincount(even_counts))
            if count > 0
        ]
        if even_counts.size
        else [],
        "quadrant_totals": quadrants.tolist(),
        "ending_totals": endings.tolist(),
    }
