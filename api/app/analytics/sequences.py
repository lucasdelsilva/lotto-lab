"""Sequencias, progressoes, repeticao entre concursos e formas no volante."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from typing import Any

import numpy as np

from app.analytics.frequency import IntArray
from app.domain.rules import ModalityRule


def max_consecutive_run(numbers: Sequence[int]) -> int:
    """Tamanho da maior sequencia de dezenas consecutivas. Uma dezena isolada vale 1."""
    if not numbers:
        return 0
    ordered = sorted(set(numbers))
    best = current = 1
    for previous, value in pairwise(ordered):
        current = current + 1 if value == previous + 1 else 1
        best = max(best, current)
    return best


def consecutive_pairs(numbers: Sequence[int]) -> int:
    """Quantidade de pares vizinhos, ou seja, quantas vezes existe d e d+1 no jogo."""
    ordered = sorted(set(numbers))
    return sum(1 for previous, value in pairwise(ordered) if value == previous + 1)


def longest_arithmetic_progression(numbers: Sequence[int]) -> tuple[int, int]:
    """Maior progressao aritmetica contida no jogo. Devolve (tamanho, passo).

    Progressao de passo 1 e a propria sequencia de consecutivos, por isso o passo tambem
    volta: uma PA de passo 5 com quatro termos e um padrao bem mais raro.
    """
    ordered = sorted(set(numbers))
    size = len(ordered)
    if size < 2:
        return (size, 0)

    best_length, best_step = 2, ordered[1] - ordered[0]
    # lengths[(j, passo)] = tamanho da PA que termina em ordered[j] com aquele passo.
    lengths: dict[tuple[int, int], int] = {}
    for j in range(size):
        for i in range(j):
            step = ordered[j] - ordered[i]
            length = lengths.get((i, step), 2) + 1 if (i, step) in lengths else 2
            lengths[(j, step)] = max(lengths.get((j, step), 2), length)
            if lengths[(j, step)] > best_length:
                best_length, best_step = lengths[(j, step)], step
    return (best_length, best_step)


def mirrors(numbers: Sequence[int], rule: ModalityRule) -> list[tuple[int, int]]:
    """Pares espelhados presentes no jogo, como 12 e 21."""
    present = set(numbers)
    found: set[tuple[int, int]] = set()
    for value in present:
        text = f"{value:02d}"
        reversed_value = int(text[::-1])
        if reversed_value == value or not rule.contains(reversed_value):
            continue
        if reversed_value in present:
            found.add((min(value, reversed_value), max(value, reversed_value)))
    return sorted(found)


def board_lines(numbers: Sequence[int], rule: ModalityRule) -> dict[str, list[int]]:
    """Linhas e colunas do volante totalmente preenchidas pelo jogo."""
    if rule.board is None:
        return {"rows": [], "cols": []}

    board = rule.board
    rows: dict[int, set[int]] = {}
    cols: dict[int, set[int]] = {}
    for value in numbers:
        row, col = board.position(value, rule.universe_min)
        rows.setdefault(row, set()).add(value)
        cols.setdefault(col, set()).add(value)

    universe = set(rule.universe())
    full_rows = []
    for row, values in rows.items():
        capacity = sum(
            1
            for candidate in universe
            if board.position(candidate, rule.universe_min)[0] == row
        )
        if len(values) == capacity:
            full_rows.append(row)

    full_cols = []
    for col, values in cols.items():
        capacity = sum(
            1
            for candidate in universe
            if board.position(candidate, rule.universe_min)[1] == col
        )
        if len(values) == capacity:
            full_cols.append(col)

    return {"rows": sorted(full_rows), "cols": sorted(full_cols)}


def repeat_from_previous(current: Sequence[int], previous: Sequence[int]) -> int:
    """Quantas dezenas do concurso atual ja estavam no concurso anterior."""
    return len(set(current) & set(previous))


def repeat_series(draws: IntArray) -> IntArray:
    """Serie historica de repeticoes em relacao ao concurso imediatamente anterior."""
    total = draws.shape[0]
    if total < 2:
        return np.zeros(0, dtype=np.int64)
    return np.array(
        [repeat_from_previous(draws[index], draws[index - 1]) for index in range(1, total)],
        dtype=np.int64,
    )


def consecutive_series(draws: IntArray) -> IntArray:
    """Serie historica do tamanho da maior sequencia de consecutivos por concurso."""
    if draws.shape[0] == 0:
        return np.zeros(0, dtype=np.int64)
    return np.array([max_consecutive_run(row.tolist()) for row in draws], dtype=np.int64)


def sequence_report(draws: IntArray, rule: ModalityRule) -> dict[str, Any]:
    """Distribuicoes historicas de consecutivos e de repeticao."""
    consecutives = consecutive_series(draws)
    repeats = repeat_series(draws)

    def histogram(values: IntArray) -> list[dict[str, int]]:
        if values.size == 0:
            return []
        counts = np.bincount(values)
        return [
            {"value": int(value), "count": int(count)}
            for value, count in enumerate(counts)
            if count > 0
        ]

    return {
        "max_consecutive": {
            "histogram": histogram(consecutives),
            "mean": round(float(consecutives.mean()), 3) if consecutives.size else 0.0,
            "p90": int(np.percentile(consecutives, 90)) if consecutives.size else 0,
        },
        "repeat_from_previous": {
            "histogram": histogram(repeats),
            "mean": round(float(repeats.mean()), 3) if repeats.size else 0.0,
            "p10": int(np.percentile(repeats, 10)) if repeats.size else 0,
            "p50": int(np.percentile(repeats, 50)) if repeats.size else 0,
            "p90": int(np.percentile(repeats, 90)) if repeats.size else 0,
        },
        "last_draw": draws[-1].tolist() if draws.shape[0] else [],
    }
