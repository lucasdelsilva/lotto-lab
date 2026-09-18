"""Analise do Super Sete.

O Super Sete nao tem dezenas, tem sete colunas independentes de 0 a 9. Toda a estatistica
e por coluna, em matrizes 7 x 10, e nada aqui reaproveita as funcoes de dezena.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from app.domain.rules import ModalityRule

DIGITS = 10
HOT_THRESHOLD = 1.5
COLD_THRESHOLD = -1.5
DEFAULT_WINDOW = 50

IntArray = npt.NDArray[np.int64]
FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class ColumnReport:
    frequency: IntArray
    relative: FloatArray
    z_scores: FloatArray
    current_delay: IntArray
    average_delay: FloatArray
    delay_ratio: FloatArray

    def as_dict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency.tolist(),
            "relative": [[round(value, 6) for value in row] for row in self.relative.tolist()],
            "z_scores": [[round(value, 4) for value in row] for row in self.z_scores.tolist()],
            "current_delay": self.current_delay.tolist(),
            "average_delay": [
                [round(value, 3) for value in row] for row in self.average_delay.tolist()
            ],
            "delay_ratio": [
                [round(value, 3) for value in row] for row in self.delay_ratio.tolist()
            ],
        }


def digit_frequency(draws: IntArray, columns: int = 7) -> IntArray:
    """Matriz colunas x 10 com a contagem de cada digito em cada coluna."""
    counts = np.zeros((columns, DIGITS), dtype=np.int64)
    if draws.shape[0] == 0:
        return counts
    for column in range(columns):
        counts[column] = np.bincount(draws[:, column], minlength=DIGITS)
    return counts


def digit_z_scores(draws: IntArray, columns: int = 7, window: int = DEFAULT_WINDOW) -> FloatArray:
    """Z-score por coluna, com p = 1/10 em cada casa."""
    effective = min(window, draws.shape[0])
    if effective == 0:
        return np.zeros((columns, DIGITS), dtype=np.float64)
    observed = digit_frequency(draws[-effective:], columns).astype(np.float64)
    p = 1.0 / DIGITS
    expected = effective * p
    deviation = float(np.sqrt(effective * p * (1.0 - p)))
    if deviation == 0.0:
        return np.zeros((columns, DIGITS), dtype=np.float64)
    return np.asarray((observed - expected) / deviation, dtype=np.float64)


def digit_delays(draws: IntArray, columns: int = 7) -> tuple[IntArray, FloatArray, FloatArray]:
    """Atraso atual, atraso medio e razao de atraso de cada digito em cada coluna."""
    current = np.zeros((columns, DIGITS), dtype=np.int64)
    average = np.zeros((columns, DIGITS), dtype=np.float64)
    total = draws.shape[0]
    if total == 0:
        return current, average, np.zeros((columns, DIGITS), dtype=np.float64)

    for column in range(columns):
        series = draws[:, column]
        for digit in range(DIGITS):
            appearances = np.flatnonzero(series == digit)
            if appearances.size == 0:
                current[column, digit] = total
                average[column, digit] = float(total)
                continue
            current[column, digit] = total - 1 - int(appearances[-1])
            leading = np.array([appearances[0]], dtype=np.int64)
            gaps = np.concatenate([leading, (np.diff(appearances) - 1).astype(np.int64)])
            average[column, digit] = float(gaps.mean())

    # Mesmo piso de 1 usado em delays.py, pela mesma razao.
    ratio = current / np.maximum(average, 1.0)
    return current, average, ratio


def column_report(
    draws: IntArray, rule: ModalityRule, window: int = DEFAULT_WINDOW
) -> ColumnReport:
    columns = rule.columns or 7
    frequency = digit_frequency(draws, columns)
    total = max(draws.shape[0], 1)
    current, average, ratio = digit_delays(draws, columns)
    return ColumnReport(
        frequency=frequency,
        relative=frequency.astype(np.float64) / float(total),
        z_scores=digit_z_scores(draws, columns, window),
        current_delay=current,
        average_delay=average,
        delay_ratio=ratio,
    )


def digit_sum_distribution(draws: IntArray) -> dict[str, Any]:
    """Distribuicao da soma dos sete digitos sorteados."""
    if draws.shape[0] == 0:
        return {"histogram": [], "p10": 0, "p50": 0, "p90": 0, "mean": 0.0}
    sums = draws.sum(axis=1)
    counts = np.bincount(sums, minlength=1)
    return {
        "histogram": [
            {"value": int(value), "count": int(count)}
            for value, count in enumerate(counts)
            if count > 0
        ],
        "p10": int(np.percentile(sums, 10)),
        "p50": int(np.percentile(sums, 50)),
        "p90": int(np.percentile(sums, 90)),
        "mean": round(float(sums.mean()), 3),
    }


def repeated_digits_distribution(draws: IntArray) -> list[dict[str, int]]:
    """Quantos digitos se repetem entre colunas no mesmo concurso."""
    if draws.shape[0] == 0:
        return []
    repeated = np.array(
        [row.shape[0] - np.unique(row).shape[0] for row in draws], dtype=np.int64
    )
    counts = np.bincount(repeated)
    return [
        {"repeated": int(value), "count": int(count)}
        for value, count in enumerate(counts)
        if count > 0
    ]


def adjacent_sequences(draws: IntArray) -> list[dict[str, int]]:
    """Quantas colunas vizinhas trazem digitos consecutivos no mesmo concurso."""
    if draws.shape[0] == 0:
        return []
    diffs = np.diff(draws, axis=1)
    runs = np.count_nonzero(np.abs(diffs) == 1, axis=1)
    counts = np.bincount(runs)
    return [
        {"adjacent": int(value), "count": int(count)}
        for value, count in enumerate(counts)
        if count > 0
    ]


def repeated_results(draws: IntArray, contests: IntArray) -> list[dict[str, Any]]:
    """Resultados completos que ja se repetiram no historico."""
    seen: dict[tuple[int, ...], list[int]] = {}
    for row, contest in zip(draws, contests, strict=True):
        key = tuple(int(value) for value in row)
        seen.setdefault(key, []).append(int(contest))
    return [
        {"result": list(key), "contests": contests_list}
        for key, contests_list in seen.items()
        if len(contests_list) > 1
    ]


def supersete_report(
    draws: IntArray, contests: IntArray, rule: ModalityRule, window: int = DEFAULT_WINDOW
) -> dict[str, Any]:
    report = column_report(draws, rule, window)
    return {
        "window": window,
        "columns": report.as_dict(),
        "sum_distribution": digit_sum_distribution(draws),
        "repeated_digits": repeated_digits_distribution(draws),
        "adjacent_sequences": adjacent_sequences(draws),
        "repeated_results": repeated_results(draws, contests),
        "last_draw": draws[-1].tolist() if draws.shape[0] else [],
    }
