from __future__ import annotations

import numpy as np

from app.analytics.sequences import (
    board_lines,
    consecutive_pairs,
    longest_arithmetic_progression,
    max_consecutive_run,
    mirrors,
    repeat_from_previous,
    repeat_series,
    sequence_report,
)
from app.domain.rules import ModalityRule


def test_maior_sequencia_de_consecutivos() -> None:
    assert max_consecutive_run([1, 2, 3, 10, 20]) == 3
    assert max_consecutive_run([1, 3, 5, 7]) == 1
    assert max_consecutive_run([5, 6, 10, 11, 12, 13]) == 4
    assert max_consecutive_run([]) == 0
    assert max_consecutive_run([42]) == 1


def test_pares_consecutivos() -> None:
    assert consecutive_pairs([1, 2, 3]) == 2
    assert consecutive_pairs([1, 2, 4, 5]) == 2
    assert consecutive_pairs([1, 3, 5]) == 0


def test_progressao_aritmetica() -> None:
    tamanho, passo = longest_arithmetic_progression([2, 7, 12, 17, 40])
    assert (tamanho, passo) == (4, 5)

    tamanho, passo = longest_arithmetic_progression([1, 2, 3, 4])
    assert (tamanho, passo) == (4, 1)

    tamanho, _ = longest_arithmetic_progression([1, 5, 12, 40])
    assert tamanho == 2


def test_espelhos(mega_rule: ModalityRule) -> None:
    assert mirrors([12, 21, 30], mega_rule) == [(12, 21)]
    assert mirrors([13, 31, 24, 42], mega_rule) == [(13, 31), (24, 42)]
    assert mirrors([11, 22, 33], mega_rule) == []


def test_espelho_fora_do_universo(lotofacil_rule: ModalityRule) -> None:
    # Na Lotofacil o universo vai ate 25, entao 13 e 31 nao formam espelho valido.
    assert mirrors([13, 24], lotofacil_rule) == []


def test_linhas_e_colunas_cheias(lotofacil_rule: ModalityRule) -> None:
    # Volante 5 x 5: a primeira linha e 1 a 5, a primeira coluna e 1, 6, 11, 16, 21.
    assert board_lines([1, 2, 3, 4, 5], lotofacil_rule)["rows"] == [0]
    assert board_lines([1, 6, 11, 16, 21], lotofacil_rule)["cols"] == [0]
    assert board_lines([1, 2, 3], lotofacil_rule) == {"rows": [], "cols": []}


def test_repeticao_em_relacao_ao_concurso_anterior() -> None:
    assert repeat_from_previous([1, 2, 3], [3, 4, 5]) == 1
    assert repeat_from_previous([1, 2, 3], [1, 2, 3]) == 3
    assert repeat_from_previous([1, 2, 3], [7, 8, 9]) == 0


def test_serie_de_repeticoes(mega_history: np.ndarray) -> None:
    # Concursos: 1-2-3-4-5-6, 1-2-7-8-9-10, 1-11..15, 1-2-3-16-17-18, 1-19..23
    assert repeat_series(mega_history).tolist() == [2, 1, 1, 1]


def test_relatorio_de_sequencias(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = sequence_report(mega_history, mega_rule)

    assert report["last_draw"] == [1, 19, 20, 21, 22, 23]
    assert report["repeat_from_previous"]["histogram"]
    assert report["max_consecutive"]["p90"] >= 1
