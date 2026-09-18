"""Verificacao de um jogo contra o historico: essa combinacao ja saiu?

Tres perguntas diferentes, respondidas por estruturas diferentes:

1. A combinacao exata ja foi sorteada? Resolve com um dicionario de frozenset.
2. Algum subconjunto do tamanho da aposta base ja foi sorteado? Vale para volantes com
   mais dezenas que o minimo, onde uma Mega com 7 dezenas contem 7 jogos de 6.
3. Qual concurso teve mais acertos em relacao a esse jogo? Resolve com produto de matriz.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np

from app.analytics.frequency import IntArray, indicator_matrix
from app.domain.rules import ModalityRule

MAX_SUBSET_COMBINATIONS = 50_000


@dataclass(frozen=True, slots=True)
class HistoricalMatch:
    contest: int | None
    hits: int

    def as_dict(self) -> dict[str, Any]:
        return {"contest": self.contest, "hits": self.hits}


class HistoryIndex:
    """Indice imutavel construido uma vez por historico e reutilizado na geracao inteira."""

    def __init__(self, draws: IntArray, contests: Sequence[int], rule: ModalityRule) -> None:
        self._rule = rule
        self._draws = draws
        self._contests = np.asarray(contests, dtype=np.int64)
        self._combos: dict[frozenset[int], list[int]] = {}
        for row, contest in zip(draws, self._contests, strict=True):
            key = frozenset(int(value) for value in row)
            self._combos.setdefault(key, []).append(int(contest))
        self._indicators = (
            indicator_matrix(draws, rule).astype(np.int16)
            if draws.shape[0]
            else np.zeros((0, rule.universe_size), dtype=np.int16)
        )

    @property
    def size(self) -> int:
        return int(self._draws.shape[0])

    @property
    def combinations_seen(self) -> int:
        return len(self._combos)

    def was_drawn(self, numbers: Sequence[int]) -> list[int]:
        """Concursos em que exatamente essa combinacao saiu."""
        return list(self._combos.get(frozenset(int(value) for value in numbers), ()))

    def contains_drawn_subset(
        self, numbers: Sequence[int], base_hits: int | None = None
    ) -> list[tuple[tuple[int, ...], list[int]]]:
        """Subconjuntos do tamanho da aposta base que ja foram sorteados.

        Um volante de 7 dezenas na Mega contem 7 combinacoes de 6. Se qualquer uma delas
        ja saiu, o volante teria sido premiado naquele concurso.
        """
        size = base_hits if base_hits is not None else self._rule.base_hits
        values = sorted(int(value) for value in numbers)
        if len(values) < size:
            return []
        if len(values) == size:
            contests = self.was_drawn(values)
            return [(tuple(values), contests)] if contests else []

        from math import comb

        if comb(len(values), size) > MAX_SUBSET_COMBINATIONS:
            # Volante muito grande para varrer subconjunto a subconjunto. A checagem por
            # interseccao maxima continua disponivel em best_historical_match.
            return []

        found: list[tuple[tuple[int, ...], list[int]]] = []
        for subset in combinations(values, size):
            subset_contests = self._combos.get(frozenset(subset))
            if subset_contests:
                found.append((subset, list(subset_contests)))
        return found

    def hits_per_contest(self, numbers: Sequence[int]) -> IntArray:
        """Quantos acertos o jogo teria feito em cada concurso do historico."""
        if self.size == 0:
            return np.zeros(0, dtype=np.int64)
        vector = np.zeros(self._rule.universe_size, dtype=np.int16)
        for value in numbers:
            vector[int(value) - self._rule.universe_min] = 1
        return (self._indicators @ vector).astype(np.int64)

    def best_historical_match(self, numbers: Sequence[int]) -> HistoricalMatch:
        """Concurso com mais acertos em relacao ao jogo. Empate resolve pelo mais recente."""
        hits = self.hits_per_contest(numbers)
        if hits.size == 0:
            return HistoricalMatch(contest=None, hits=0)
        best = int(hits.max())
        candidates = np.flatnonzero(hits == best)
        contest = int(self._contests[candidates[-1]])
        return HistoricalMatch(contest=contest, hits=best)

    def evaluate(self, numbers: Sequence[int]) -> dict[str, Any]:
        """Resumo usado pelo gerador para preencher already_drawn e matched_contests."""
        exact = self.was_drawn(numbers)
        subsets = self.contains_drawn_subset(numbers)
        matched = sorted({contest for _, contests in subsets for contest in contests} | set(exact))
        return {
            "already_drawn": bool(exact) or bool(subsets),
            "exact_contests": exact,
            "drawn_subsets": [
                {"numbers": list(subset), "contests": contests} for subset, contests in subsets
            ],
            "matched_contests": matched,
            "best_historical_match": self.best_historical_match(numbers).as_dict(),
        }
