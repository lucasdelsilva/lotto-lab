from __future__ import annotations

import numpy as np

from app.analytics.delays import delay_matrix, delay_report
from app.domain.rules import ModalityRule


def test_atraso_atual(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = delay_report(mega_history, mega_rule)

    # A dezena 1 saiu no ultimo concurso, entao o atraso e zero.
    assert report.current[0] == 0
    # A dezena 2 saiu pela ultima vez no quarto de cinco concursos.
    assert report.current[1] == 1
    # A dezena 7 saiu apenas no segundo concurso.
    assert report.current[6] == 3
    # A dezena 60 nunca saiu, o atraso e o historico inteiro.
    assert report.current[59] == 5


def test_atraso_medio_e_maximo(mega_rule: ModalityRule) -> None:
    # Dezena 1 sai nos concursos de indice 0, 2 e 4. Intervalos: 0 antes da primeira,
    # 1 entre a primeira e a segunda, 1 entre a segunda e a terceira.
    draws = np.asarray(
        [
            [1, 10, 11, 12, 13, 14],
            [2, 10, 11, 12, 13, 14],
            [1, 10, 11, 12, 13, 14],
            [2, 10, 11, 12, 13, 14],
            [1, 10, 11, 12, 13, 14],
        ],
        dtype=np.int64,
    )
    report = delay_report(draws, mega_rule)

    assert report.current[0] == 0
    assert report.average[0] == (0 + 1 + 1) / 3
    assert report.maximum[0] == 1


def test_razao_de_atraso_marca_dezena_atrasada(mega_rule: ModalityRule) -> None:
    # Dezena 1 sai com folga nos primeiros concursos e depois some por muito tempo.
    rows = [[1, 20, 21, 22, 23, 24] for _ in range(5)]
    rows += [[2, 20, 21, 22, 23, 24] for _ in range(20)]
    draws = np.asarray(rows, dtype=np.int64)

    report = delay_report(draws, mega_rule)
    assert report.current[0] == 20
    assert report.ratio[0] > 1.5
    assert 1 in report.overdue().tolist()


def test_dezena_recorrente_nao_e_atrasada(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = delay_report(mega_history, mega_rule)
    assert report.ratio[0] == 0.0
    assert 1 not in report.overdue().tolist()


def test_serie_para_o_heatmap(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    series = delay_matrix(mega_history, mega_rule, last_n=3)
    assert series.shape == (60, 3)
    # A dezena 1 sai em todos os concursos, entao o atraso e sempre zero.
    assert series[0].tolist() == [0, 0, 0]
    # A dezena 60 nunca sai, o contador cresce a cada concurso.
    assert series[59].tolist() == [3, 4, 5]


def test_historico_vazio(mega_rule: ModalityRule) -> None:
    vazio = np.zeros((0, 6), dtype=np.int64)
    report = delay_report(vazio, mega_rule)
    assert report.current.sum() == 0
    assert delay_matrix(vazio, mega_rule).shape == (60, 0)
