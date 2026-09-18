from decimal import Decimal

import pytest

from app.domain.enums import Modality
from app.domain.rules import MODALITY_RULES, rule_for


def test_todas_as_modalidades_tem_regra() -> None:
    assert set(MODALITY_RULES) == set(Modality)


@pytest.mark.parametrize(
    ("modality", "universo", "minimo", "maximo", "acertos", "preco"),
    [
        (Modality.MEGA_SENA, 60, 6, 20, 6, "6.00"),
        (Modality.LOTOFACIL, 25, 15, 20, 15, "3.50"),
        (Modality.QUINA, 80, 5, 15, 5, "3.00"),
        (Modality.DIA_DE_SORTE, 31, 7, 15, 7, "2.50"),
        (Modality.SUPER_SETE, 10, 7, 21, 7, "3.00"),
    ],
)
def test_parametros_oficiais(
    modality: Modality, universo: int, minimo: int, maximo: int, acertos: int, preco: str
) -> None:
    rule = rule_for(modality)
    assert rule.universe_size == universo
    assert rule.min_pick == minimo
    assert rule.max_pick == maximo
    assert rule.base_hits == acertos
    assert rule.base_price == Decimal(preco)


def test_board_cobre_todo_o_universo() -> None:
    for modality in (Modality.MEGA_SENA, Modality.LOTOFACIL, Modality.QUINA, Modality.DIA_DE_SORTE):
        rule = rule_for(modality)
        assert rule.board is not None
        assert rule.board.rows * rule.board.cols >= rule.universe_size


def test_quadrantes_da_lotofacil() -> None:
    rule = rule_for(Modality.LOTOFACIL)
    assert rule.board is not None
    # Volante 5 x 5. A metade superior fica com as linhas 0 e 1, a esquerda com as colunas 0 e 1.
    assert rule.board.quadrant(1, rule.universe_min) == 0
    assert rule.board.quadrant(5, rule.universe_min) == 1
    assert rule.board.quadrant(21, rule.universe_min) == 2
    assert rule.board.quadrant(25, rule.universe_min) == 3


def test_dia_de_sorte_exige_mes() -> None:
    rule = rule_for(Modality.DIA_DE_SORTE)
    assert rule.extra_schema["month"]["required"] is True
    assert rule.extra_schema["month"]["count"] == 1


def test_super_sete_e_baseado_em_colunas() -> None:
    rule = rule_for(Modality.SUPER_SETE)
    assert rule.is_column_based
    assert rule.columns == 7
    assert (rule.column_min_pick, rule.column_max_pick) == (1, 3)
    assert rule.board is None
