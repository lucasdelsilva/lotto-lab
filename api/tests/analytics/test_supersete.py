from __future__ import annotations

import numpy as np

from app.analytics.supersete import (
    adjacent_sequences,
    column_report,
    digit_delays,
    digit_frequency,
    digit_sum_distribution,
    digit_z_scores,
    repeated_digits_distribution,
    repeated_results,
    supersete_report,
)
from app.domain.rules import ModalityRule


def history() -> np.ndarray:
    return np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 7],
            [1, 0, 0, 0, 0, 0, 0],
            [1, 2, 3, 4, 5, 6, 7],
            [9, 9, 9, 9, 9, 9, 9],
        ],
        dtype=np.int64,
    )


def test_frequencia_por_coluna() -> None:
    counts = digit_frequency(history())

    assert counts.shape == (7, 10)
    # Coluna 0: o digito 1 apareceu tres vezes, o 9 apareceu uma.
    assert counts[0, 1] == 3
    assert counts[0, 9] == 1
    assert counts[0].sum() == 4


def test_z_score_por_coluna() -> None:
    z = digit_z_scores(history(), window=4)

    assert z.shape == (7, 10)
    # O digito 1 na coluna 0 saiu muito acima do esperado de 0,4 aparicoes.
    assert z[0, 1] > 1.5


def test_atraso_por_coluna() -> None:
    current, _average, ratio = digit_delays(history())

    assert current.shape == (7, 10)
    # Coluna 0: o digito 9 saiu no ultimo concurso.
    assert current[0, 9] == 0
    # Coluna 0: o digito 1 saiu pela ultima vez no penultimo concurso.
    assert current[0, 1] == 1
    # Digito que nunca apareceu na coluna fica com o atraso igual ao historico inteiro.
    assert current[0, 5] == 4
    assert ratio.shape == (7, 10)


def test_distribuicao_da_soma() -> None:
    distribution = digit_sum_distribution(history())

    # Somas: 28, 1, 28 e 63.
    assert distribution["mean"] == round((28 + 1 + 28 + 63) / 4, 3)
    assert {item["value"] for item in distribution["histogram"]} == {1, 28, 63}


def test_digitos_repetidos_entre_colunas() -> None:
    distribution = repeated_digits_distribution(history())
    counts = {item["repeated"]: item["count"] for item in distribution}

    # O concurso 1-2-3-4-5-6-7 nao repete nenhum digito, aparece duas vezes.
    assert counts[0] == 2
    # O concurso 9-9-9-9-9-9-9 tem um digito distinto, logo seis repetidos.
    assert counts[6] == 1
    # O concurso 1-0-0-0-0-0-0 tem dois digitos distintos, logo cinco repetidos.
    assert counts[5] == 1


def test_sequencias_entre_colunas_vizinhas() -> None:
    distribution = adjacent_sequences(history())
    counts = {item["adjacent"]: item["count"] for item in distribution}

    # 1-2-3-4-5-6-7 tem seis pares vizinhos consecutivos, e aparece duas vezes.
    assert counts[6] == 2


def test_resultado_completo_repetido() -> None:
    contests = np.array([10, 11, 12, 13], dtype=np.int64)
    repeated = repeated_results(history(), contests)

    assert len(repeated) == 1
    assert repeated[0]["result"] == [1, 2, 3, 4, 5, 6, 7]
    assert repeated[0]["contests"] == [10, 12]


def test_relatorio_completo(supersete_rule: ModalityRule) -> None:
    contests = np.array([10, 11, 12, 13], dtype=np.int64)
    report = supersete_report(history(), contests, supersete_rule, window=4)

    assert len(report["columns"]["frequency"]) == 7
    assert len(report["columns"]["frequency"][0]) == 10
    assert report["last_draw"] == [9, 9, 9, 9, 9, 9, 9]


def test_historico_vazio(supersete_rule: ModalityRule) -> None:
    vazio = np.zeros((0, 7), dtype=np.int64)
    report = column_report(vazio, supersete_rule)

    assert report.frequency.sum() == 0
    assert repeated_digits_distribution(vazio) == []
