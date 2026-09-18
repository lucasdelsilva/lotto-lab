from __future__ import annotations

import numpy as np

from app.analytics.frequency import (
    absolute_frequency,
    classify,
    expected_probability,
    frequency_report,
    indicator_matrix,
    relative_frequency,
    window_frequency,
    z_scores,
)
from app.domain.enums import NumberTemperature
from app.domain.rules import ModalityRule


def test_frequencia_absoluta(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    freq = absolute_frequency(mega_history, mega_rule)
    assert freq.shape == (60,)
    assert freq[0] == 5  # dezena 1 saiu nos cinco concursos
    assert freq[1] == 3  # dezena 2 saiu em tres
    assert freq[59] == 0  # dezena 60 nunca saiu
    assert int(freq.sum()) == mega_history.size


def test_frequencia_relativa(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    rate = relative_frequency(mega_history, mega_rule)
    assert rate[0] == 1.0
    assert rate[1] == 0.6
    assert rate[59] == 0.0


def test_probabilidade_esperada(mega_rule: ModalityRule, lotofacil_rule: ModalityRule) -> None:
    assert expected_probability(mega_rule) == 6 / 60
    assert expected_probability(lotofacil_rule) == 15 / 25


def test_matriz_indicadora(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    indicators = indicator_matrix(mega_history, mega_rule)
    assert indicators.shape == (5, 60)
    assert indicators[0, 0] == 1
    assert indicators[0, 6] == 0
    assert int(indicators.sum()) == mega_history.size


def test_janela_movel(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    ultimos_dois = window_frequency(mega_history, mega_rule, 2)
    assert ultimos_dois[0] == 2  # dezena 1 nos dois ultimos
    assert ultimos_dois[1] == 1  # dezena 2 apenas no concurso 104
    assert ultimos_dois[6] == 0  # dezena 7 ficou fora da janela


def test_z_score_bate_com_a_formula(mega_rule: ModalityRule) -> None:
    # Dezena 1 em todos os 30 concursos, o resto preenchido por dezenas distintas.
    rows = [[1, 2 + (i % 50), 55, 56, 57, 58] for i in range(30)]
    draws = np.asarray(rows, dtype=np.int64)

    z = z_scores(draws, mega_rule, window=30)
    p = 6 / 60
    esperado = 30 * p
    desvio = (30 * p * (1 - p)) ** 0.5
    assert z[0] == ((30 - esperado) / desvio)
    assert z[0] > 1.5


def test_classificacao_quente_fria_neutra() -> None:
    assert classify(2.0) is NumberTemperature.HOT
    assert classify(1.5) is NumberTemperature.HOT
    assert classify(-1.5) is NumberTemperature.COLD
    assert classify(0.0) is NumberTemperature.NEUTRAL


def test_relatorio_completo(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = frequency_report(mega_history, mega_rule, windows=(2, 5))
    payload = report.as_dict()

    assert payload["numbers"][0] == 1
    assert payload["ranking"][0] == 1  # dezena mais frequente lidera o ranking
    assert set(payload["windows"]) == {"2", "5"}
    assert len(payload["histogram"]) == 60


def test_historico_vazio(mega_rule: ModalityRule) -> None:
    vazio = np.zeros((0, 6), dtype=np.int64)
    assert absolute_frequency(vazio, mega_rule).sum() == 0
    assert z_scores(vazio, mega_rule, 50).sum() == 0
