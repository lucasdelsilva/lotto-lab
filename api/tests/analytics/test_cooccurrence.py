from __future__ import annotations

import numpy as np

from app.analytics.cooccurrence import (
    average_lift_with,
    cooccurrence_report,
    markov_transition,
    next_draw_probability,
    pair_counts,
    pair_lift,
    top_triples,
)
from app.domain.rules import ModalityRule


def test_contagem_de_pares(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    counts = pair_counts(mega_history, mega_rule)

    assert counts.shape == (60, 60)
    # A diagonal guarda a frequencia individual.
    assert counts[0, 0] == 5
    # Dezenas 1 e 2 sairam juntas em tres concursos.
    assert counts[0, 1] == 3
    assert counts[1, 0] == 3
    # Dezenas 2 e 11 nunca sairam juntas.
    assert counts[1, 10] == 0


def test_lift_acima_de_um_para_par_associado(mega_rule: ModalityRule) -> None:
    # Dezenas 1 e 2 sempre saem juntas, 1 e 3 nunca.
    draws = np.asarray(
        [
            [1, 2, 10, 11, 12, 13],
            [1, 2, 14, 15, 16, 17],
            [3, 4, 10, 11, 12, 13],
            [3, 4, 14, 15, 16, 17],
        ],
        dtype=np.int64,
    )
    counts = pair_counts(draws, mega_rule)
    lift = pair_lift(counts, draws.shape[0])

    assert lift[0, 1] == 2.0  # P(1 e 2) = 0.5, P(1) * P(2) = 0.25
    assert lift[0, 2] == 0.0  # nunca juntas
    assert lift[0, 0] == 0.0  # a diagonal e zerada de proposito


def test_trincas_mais_frequentes(mega_history: np.ndarray) -> None:
    triples = top_triples(mega_history, limit=5)

    assert triples[0]["count"] >= triples[-1]["count"]
    assert all(len(item["triple"]) == 3 for item in triples)


def test_transicao_de_markov(mega_rule: ModalityRule) -> None:
    # A dezena 1 sempre e seguida pela dezena 5 no concurso seguinte.
    draws = np.asarray(
        [
            [1, 20, 21, 22, 23, 24],
            [5, 30, 31, 32, 33, 34],
            [1, 20, 21, 22, 23, 24],
            [5, 30, 31, 32, 33, 34],
        ],
        dtype=np.int64,
    )
    transition = markov_transition(draws, mega_rule)

    assert transition.shape == (60, 60)
    assert transition[0, 4] == 1.0  # dezena 1 seguida da dezena 5
    assert transition[0, 0] == 0.0  # dezena 1 nunca se repete no concurso seguinte


def test_probabilidade_do_proximo_concurso(mega_rule: ModalityRule) -> None:
    draws = np.asarray(
        [
            [1, 20, 21, 22, 23, 24],
            [5, 30, 31, 32, 33, 34],
            [1, 20, 21, 22, 23, 24],
            [5, 30, 31, 32, 33, 34],
        ],
        dtype=np.int64,
    )
    transition = markov_transition(draws, mega_rule)
    probabilities = next_draw_probability(transition, draws[-1], mega_rule)

    assert probabilities.shape == (60,)
    assert probabilities[0] > 0.0  # o ultimo concurso puxa a dezena 1 de volta


def test_lift_medio_com_as_selecionadas(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = cooccurrence_report(mega_history, mega_rule)
    medio = average_lift_with(report.lift, [1], mega_rule)

    assert medio.shape == (60,)
    assert medio[1] > 0.0  # dezena 2 acompanha a dezena 1
    assert medio[59] == 0.0  # dezena 60 nunca saiu


def test_relatorio_de_co_ocorrencia(mega_history: np.ndarray, mega_rule: ModalityRule) -> None:
    report = cooccurrence_report(mega_history, mega_rule)
    payload = report.as_dict()

    assert payload["top_pairs"][0]["count"] == 3  # par 1 e 2
    assert payload["top_pairs"][0]["pair"] == [1, 2]
    assert [2, 11] in payload["never_together"]


def test_historico_vazio(mega_rule: ModalityRule) -> None:
    vazio = np.zeros((0, 6), dtype=np.int64)
    counts = pair_counts(vazio, mega_rule)

    assert counts.sum() == 0
    assert pair_lift(counts, 0).sum() == 0
    assert markov_transition(vazio, mega_rule).sum() == 0
