"""Frequencia das dezenas. Funcoes puras sobre arrays NumPy.

Convencao usada em todo o pacote analytics: `draws` e um array de inteiros com forma
(n_concursos, dezenas_por_concurso), em ordem cronologica crescente. A ultima linha e o
concurso mais recente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from app.domain.enums import NumberTemperature
from app.domain.rules import ModalityRule

HOT_THRESHOLD = 1.5
COLD_THRESHOLD = -1.5
DEFAULT_WINDOWS: tuple[int, ...] = (25, 50, 100, 200)

IntArray = npt.NDArray[np.int64]
FloatArray = npt.NDArray[np.float64]


def as_matrix(draws: list[tuple[int, ...]] | IntArray) -> IntArray:
    """Normaliza o historico para um array (n_concursos, dezenas)."""
    matrix = np.asarray(draws, dtype=np.int64)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    return matrix


def indicator_matrix(draws: IntArray, rule: ModalityRule) -> npt.NDArray[np.int8]:
    """Matriz binaria (n_concursos, universo): 1 quando a dezena saiu no concurso."""
    total, _ = draws.shape
    matrix = np.zeros((total, rule.universe_size), dtype=np.int8)
    rows = np.repeat(np.arange(total), draws.shape[1])
    cols = (draws - rule.universe_min).ravel()
    matrix[rows, cols] = 1
    return matrix


def absolute_frequency(draws: IntArray, rule: ModalityRule) -> IntArray:
    """Quantas vezes cada dezena saiu no historico informado."""
    if draws.size == 0:
        return np.zeros(rule.universe_size, dtype=np.int64)
    flat = draws.ravel() - rule.universe_min
    return np.bincount(flat, minlength=rule.universe_size).astype(np.int64)


def expected_probability(rule: ModalityRule) -> float:
    """Probabilidade de uma dezena especifica sair em um concurso qualquer."""
    return rule.base_hits / rule.universe_size


def relative_frequency(draws: IntArray, rule: ModalityRule) -> FloatArray:
    """Fracao dos concursos em que cada dezena apareceu."""
    total = draws.shape[0]
    if total == 0:
        return np.zeros(rule.universe_size, dtype=np.float64)
    return absolute_frequency(draws, rule).astype(np.float64) / float(total)


def window_frequency(draws: IntArray, rule: ModalityRule, window: int) -> IntArray:
    """Frequencia absoluta considerando apenas os ultimos `window` concursos."""
    if window <= 0:
        raise ValueError("A janela precisa ser positiva.")
    return absolute_frequency(draws[-window:], rule)


def z_scores(draws: IntArray, rule: ModalityRule, window: int) -> FloatArray:
    """Z-score por janela, com aproximacao binomial.

    esperado = W * p, desvio = sqrt(W * p * (1 - p)), z = (observado - esperado) / desvio.
    """
    effective = min(window, draws.shape[0])
    if effective == 0:
        return np.zeros(rule.universe_size, dtype=np.float64)
    observed = window_frequency(draws, rule, effective).astype(np.float64)
    p = expected_probability(rule)
    expected = effective * p
    deviation = float(np.sqrt(effective * p * (1.0 - p)))
    if deviation == 0.0:
        return np.zeros(rule.universe_size, dtype=np.float64)
    return np.asarray((observed - expected) / deviation, dtype=np.float64)


def classify(z: float) -> NumberTemperature:
    if z >= HOT_THRESHOLD:
        return NumberTemperature.HOT
    if z <= COLD_THRESHOLD:
        return NumberTemperature.COLD
    return NumberTemperature.NEUTRAL


def classify_all(z_values: FloatArray) -> list[NumberTemperature]:
    return [classify(float(value)) for value in z_values]


@dataclass(frozen=True, slots=True)
class FrequencyReport:
    numbers: IntArray
    absolute: IntArray
    relative: FloatArray
    expected_rate: float
    windows: dict[int, IntArray]
    z_by_window: dict[int, FloatArray]
    ranking: IntArray

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_rate": self.expected_rate,
            "numbers": self.numbers.tolist(),
            "absolute": self.absolute.tolist(),
            "relative": [round(value, 6) for value in self.relative.tolist()],
            "windows": {
                str(window): counts.tolist() for window, counts in self.windows.items()
            },
            "z_by_window": {
                str(window): [round(value, 4) for value in values.tolist()]
                for window, values in self.z_by_window.items()
            },
            "ranking": self.ranking.tolist(),
            "histogram": [
                {"n": int(n), "count": int(count), "rate": round(float(rate), 6)}
                for n, count, rate in zip(
                    self.numbers, self.absolute, self.relative, strict=True
                )
            ],
        }


def frequency_report(
    draws: IntArray, rule: ModalityRule, windows: tuple[int, ...] = DEFAULT_WINDOWS
) -> FrequencyReport:
    numbers = np.arange(rule.universe_min, rule.universe_max + 1, dtype=np.int64)
    absolute = absolute_frequency(draws, rule)
    relative = relative_frequency(draws, rule)
    window_counts = {window: window_frequency(draws, rule, window) for window in windows}
    z_values = {window: z_scores(draws, rule, window) for window in windows}
    ranking = numbers[np.argsort(-absolute, kind="stable")]
    return FrequencyReport(
        numbers=numbers,
        absolute=absolute,
        relative=relative,
        expected_rate=expected_probability(rule),
        windows=window_counts,
        z_by_window=z_values,
        ranking=ranking,
    )
