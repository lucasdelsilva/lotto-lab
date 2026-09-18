from __future__ import annotations

import numpy as np

from app.analytics.history_index import HistoryIndex
from app.domain.rules import ModalityRule


def test_combinacao_exata_ja_sorteada(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)

    assert index.was_drawn([1, 2, 3, 4, 5, 6]) == [101]
    # A ordem das dezenas nao importa.
    assert index.was_drawn([6, 5, 4, 3, 2, 1]) == [101]
    assert index.was_drawn([7, 8, 9, 10, 11, 12]) == []


def test_combinacao_repetida_lista_todos_os_concursos(mega_rule: ModalityRule) -> None:
    draws = np.asarray(
        [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [1, 2, 3, 4, 5, 6]], dtype=np.int64
    )
    index = HistoryIndex(draws, [10, 11, 12], mega_rule)

    assert index.was_drawn([1, 2, 3, 4, 5, 6]) == [10, 12]
    assert index.combinations_seen == 2


def test_subconjunto_ja_sorteado(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    # Volante de sete dezenas que contem o concurso 101 inteiro.
    subsets = index.contains_drawn_subset([1, 2, 3, 4, 5, 6, 59])

    assert len(subsets) == 1
    combinacao, concursos = subsets[0]
    assert combinacao == (1, 2, 3, 4, 5, 6)
    assert concursos == [101]


def test_sem_subconjunto_sorteado(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    assert index.contains_drawn_subset([30, 31, 32, 33, 34, 35, 36]) == []


def test_melhor_correspondencia_historica(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    match = index.best_historical_match([1, 2, 3, 4, 5, 60])

    assert match.hits == 5
    assert match.contest == 101


def test_acertos_por_concurso(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    hits = index.hits_per_contest([1, 2, 3, 4, 5, 6])

    assert hits.tolist() == [6, 2, 1, 3, 1]


def test_avaliacao_completa(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    evaluation = index.evaluate([1, 2, 3, 4, 5, 6])

    assert evaluation["already_drawn"] is True
    assert evaluation["matched_contests"] == [101]
    assert evaluation["best_historical_match"] == {"contest": 101, "hits": 6}


def test_jogo_inedito(
    mega_history: np.ndarray, mega_contests: np.ndarray, mega_rule: ModalityRule
) -> None:
    index = HistoryIndex(mega_history, mega_contests.tolist(), mega_rule)
    evaluation = index.evaluate([31, 32, 33, 34, 35, 36])

    assert evaluation["already_drawn"] is False
    assert evaluation["matched_contests"] == []
    assert evaluation["best_historical_match"]["hits"] == 0


def test_historico_vazio(mega_rule: ModalityRule) -> None:
    index = HistoryIndex(np.zeros((0, 6), dtype=np.int64), [], mega_rule)

    assert index.size == 0
    assert index.was_drawn([1, 2, 3, 4, 5, 6]) == []
    assert index.best_historical_match([1, 2, 3, 4, 5, 6]).contest is None
