"""Atraso das dezenas: ha quantos concursos cada uma nao aparece.

Definicao usada: o atraso de uma dezena no concurso t e a quantidade de concursos desde a
ultima aparicao. Se a dezena saiu no ultimo concurso, o atraso atual e zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from app.analytics.frequency import FloatArray, IntArray, indicator_matrix
from app.domain.rules import ModalityRule

OVERDUE_RATIO = 1.5


@dataclass(frozen=True, slots=True)
class DelayReport:
    numbers: IntArray
    current: IntArray
    average: FloatArray
    deviation: FloatArray
    maximum: IntArray
    ratio: FloatArray

    def overdue(self) -> IntArray:
        return self.numbers[self.ratio >= OVERDUE_RATIO]

    def as_dict(self) -> dict[str, Any]:
        return {
            "numbers": self.numbers.tolist(),
            "current": self.current.tolist(),
            "average": [round(value, 3) for value in self.average.tolist()],
            "deviation": [round(value, 3) for value in self.deviation.tolist()],
            "maximum": self.maximum.tolist(),
            "ratio": [round(value, 3) for value in self.ratio.tolist()],
            "overdue": self.overdue().tolist(),
            "rows": [
                {
                    "n": int(n),
                    "current": int(current),
                    "average": round(float(average), 3),
                    "deviation": round(float(deviation), 3),
                    "maximum": int(maximum),
                    "ratio": round(float(ratio), 3),
                }
                for n, current, average, deviation, maximum, ratio in zip(
                    self.numbers,
                    self.current,
                    self.average,
                    self.deviation,
                    self.maximum,
                    self.ratio,
                    strict=True,
                )
            ],
        }


def _gaps_for(appearances: IntArray, total: int) -> IntArray:
    """Intervalos sem a dezena: antes da primeira aparicao e entre aparicoes consecutivas."""
    if appearances.size == 0:
        return np.array([total], dtype=np.int64)
    leading = np.array([appearances[0]], dtype=np.int64)
    between = np.diff(appearances) - 1
    return np.concatenate([leading, between.astype(np.int64)])


def delay_report(draws: IntArray, rule: ModalityRule) -> DelayReport:
    numbers = np.arange(rule.universe_min, rule.universe_max + 1, dtype=np.int64)
    total = draws.shape[0]
    if total == 0:
        zeros_i = np.zeros(rule.universe_size, dtype=np.int64)
        zeros_f = np.zeros(rule.universe_size, dtype=np.float64)
        return DelayReport(numbers, zeros_i, zeros_f, zeros_f, zeros_i, zeros_f)

    indicators = indicator_matrix(draws, rule)
    current = np.zeros(rule.universe_size, dtype=np.int64)
    average = np.zeros(rule.universe_size, dtype=np.float64)
    deviation = np.zeros(rule.universe_size, dtype=np.float64)
    maximum = np.zeros(rule.universe_size, dtype=np.int64)

    for index in range(rule.universe_size):
        appearances = np.flatnonzero(indicators[:, index]).astype(np.int64)
        if appearances.size == 0:
            current[index] = total
            average[index] = float(total)
            maximum[index] = total
            continue
        current[index] = total - 1 - int(appearances[-1])
        gaps = _gaps_for(appearances, total)
        average[index] = float(gaps.mean())
        deviation[index] = float(gaps.std())
        maximum[index] = int(max(gaps.max(), current[index]))

    # Piso de 1 no denominador: uma dezena que historicamente sai em todo concurso tem
    # atraso medio zero, e sem o piso qualquer ausencia dela ficaria com razao zero.
    ratio = current / np.maximum(average, 1.0)

    return DelayReport(
        numbers=numbers,
        current=current,
        average=average,
        deviation=deviation,
        maximum=maximum,
        ratio=np.nan_to_num(ratio, nan=0.0, posinf=0.0),
    )


def delay_matrix(draws: IntArray, rule: ModalityRule, last_n: int = 60) -> npt.NDArray[np.int64]:
    """Serie temporal de atrasos (universo x ultimos concursos), pronta para o heatmap."""
    total = draws.shape[0]
    if total == 0:
        return np.zeros((rule.universe_size, 0), dtype=np.int64)

    indicators = indicator_matrix(draws, rule)
    series = np.zeros((rule.universe_size, total), dtype=np.int64)
    counters = np.zeros(rule.universe_size, dtype=np.int64)
    for step in range(total):
        present = indicators[step].astype(bool)
        counters = counters + 1
        counters[present] = 0
        series[:, step] = counters

    window = min(last_n, total)
    return series[:, total - window :]
