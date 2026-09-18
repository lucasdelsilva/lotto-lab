from __future__ import annotations

import numpy as np

from app.analytics.patterns import (
    PRIMES,
    describe_game,
    ending_counts,
    fit_score,
    historical_metrics,
    pattern_report,
    percentile_ranges,
    quadrant_counts,
)
from app.domain.rules import ModalityRule


def test_metricas_de_um_jogo_conhecido(mega_rule: ModalityRule) -> None:
    jogo = [4, 12, 23, 38, 47, 55]
    metrics = describe_game(jogo, mega_rule)

    assert metrics.total_sum == 179
    assert metrics.even_count == 3  # 4, 12, 38
    assert metrics.odd_count == 3  # 23, 47, 55
    assert metrics.prime_count == 2  # 23 e 47
    assert metrics.spread == 51  # 55 menos 4
    assert metrics.max_consecutive == 1
    assert metrics.consecutive_pairs == 0
    assert metrics.multiples_of_3 == 1  # apenas o 12
    assert metrics.multiples_of_5 == 1  # apenas o 55


def test_multiplos_de_tres(mega_rule: ModalityRule) -> None:
    metrics = describe_game([3, 6, 9, 10, 11, 13], mega_rule)
    assert metrics.multiples_of_3 == 3
    assert metrics.multiples_of_5 == 1  # apenas o 10


def test_primos_conhecidos() -> None:
    assert 2 in PRIMES
    assert 23 in PRIMES
    assert 1 not in PRIMES
    assert 57 not in PRIMES  # 57 = 3 x 19


def test_consecutivos_no_jogo(mega_rule: ModalityRule) -> None:
    metrics = describe_game([1, 2, 3, 10, 20, 30], mega_rule)
    assert metrics.max_consecutive == 3
    assert metrics.consecutive_pairs == 2


def test_terminacoes() -> None:
    counts = ending_counts([5, 15, 25, 7, 60])
    assert counts[5] == 3
    assert counts[7] == 1
    assert counts[0] == 1
    assert counts[1] == 0


def test_quadrantes_da_lotofacil(lotofacil_rule: ModalityRule) -> None:
    # Volante 5 x 5: 1 a 5 na primeira linha, 21 a 25 na ultima.
    counts = quadrant_counts([1, 2, 4, 5, 21, 25], lotofacil_rule)
    assert counts == (2, 2, 1, 1)


def test_quadrantes_somam_o_total_de_dezenas(mega_rule: ModalityRule) -> None:
    jogo = [1, 15, 29, 33, 47, 60]
    assert sum(quadrant_counts(jogo, mega_rule)) == len(jogo)


def test_metricas_historicas(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    series = historical_metrics(mega_history, mega_rule)

    assert series["sum"].tolist() == [21, 37, 66, 57, 106]
    assert series["spread"].tolist() == [5, 9, 14, 17, 22]
    assert series["sum"].shape[0] == mega_history.shape[0]


def test_percentis(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    ranges = percentile_ranges(historical_metrics(mega_history, mega_rule))

    assert ranges["sum"]["min"] == 21.0
    assert ranges["sum"]["max"] == 106.0
    assert ranges["sum"]["p10"] <= ranges["sum"]["p50"] <= ranges["sum"]["p90"]


def test_fit_score_premia_jogo_dentro_da_faixa(mega_rule: ModalityRule) -> None:
    ranges = {
        "sum": {"p10": 150.0, "p90": 250.0},
        "even": {"p10": 2.0, "p90": 4.0},
        "primes": {"p10": 1.0, "p90": 3.0},
        "spread": {"p10": 30.0, "p90": 55.0},
        "max_consecutive": {"p10": 1.0, "p90": 2.0},
        "multiples_of_3": {"p10": 1.0, "p90": 3.0},
        "multiples_of_5": {"p10": 0.0, "p90": 2.0},
    }
    dentro = describe_game([4, 12, 23, 38, 47, 55], mega_rule)
    assert fit_score(dentro, ranges) == 1.0


def test_fit_score_penaliza_jogo_fora_da_faixa(mega_rule: ModalityRule) -> None:
    ranges = {
        "sum": {"p10": 150.0, "p90": 250.0},
        "even": {"p10": 2.0, "p90": 4.0},
        "primes": {"p10": 1.0, "p90": 3.0},
        "spread": {"p10": 30.0, "p90": 55.0},
        "max_consecutive": {"p10": 1.0, "p90": 2.0},
        "multiples_of_3": {"p10": 1.0, "p90": 3.0},
        "multiples_of_5": {"p10": 0.0, "p90": 2.0},
    }
    fora = describe_game([1, 2, 3, 4, 5, 6], mega_rule)
    score = fit_score(fora, ranges)
    assert 0.0 <= score < 1.0
    assert score < fit_score(describe_game([4, 12, 23, 38, 47, 55], mega_rule), ranges)


def test_relatorio_de_padroes(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = pattern_report(mega_history, mega_rule)

    assert "sum" in report["ranges"]
    assert sum(report["quadrant_totals"]) == mega_history.size
    assert sum(report["ending_totals"]) == mega_history.size
    assert report["sum_histogram"]
