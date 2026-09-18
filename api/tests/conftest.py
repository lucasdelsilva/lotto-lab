"""Fixtures compartilhadas. Os historicos sinteticos tem resultado conhecido de proposito."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from app.domain.enums import Modality
from app.domain.rules import ModalityRule, rule_for


def matrix(rows: Sequence[Sequence[int]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.int64)


@pytest.fixture
def mega_rule() -> ModalityRule:
    return rule_for(Modality.MEGA_SENA)


@pytest.fixture
def lotofacil_rule() -> ModalityRule:
    return rule_for(Modality.LOTOFACIL)


@pytest.fixture
def supersete_rule() -> ModalityRule:
    return rule_for(Modality.SUPER_SETE)


@pytest.fixture
def mega_history() -> np.ndarray:
    """Cinco concursos da Mega em que a dezena 1 sai sempre e a dezena 60 nunca sai."""
    return matrix(
        [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 7, 8, 9, 10],
            [1, 11, 12, 13, 14, 15],
            [1, 2, 3, 16, 17, 18],
            [1, 19, 20, 21, 22, 23],
        ]
    )


@pytest.fixture
def mega_contests() -> np.ndarray:
    return np.array([101, 102, 103, 104, 105], dtype=np.int64)


def random_history(
    rule: ModalityRule, draws_count: int, seed: int = 7, size: int | None = None
) -> np.ndarray:
    """Historico pseudoaleatorio uniforme, usado como grupo de controle nos testes."""
    rng = np.random.default_rng(seed)
    picks = size or rule.base_hits
    universe = np.arange(rule.universe_min, rule.universe_max + 1)
    rows = [np.sort(rng.choice(universe, size=picks, replace=False)) for _ in range(draws_count)]
    return np.asarray(rows, dtype=np.int64)
