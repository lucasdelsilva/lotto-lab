from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import ValidationError
from app.domain.enums import Modality
from app.domain.pricing import (
    batch_cost,
    combinations,
    distribute_columns,
    game_count,
    money,
    preview_cost,
)
from app.domain.rules import rule_for


class TestCombinatoria:
    def test_combinacao_simples(self) -> None:
        assert combinations(6, 6) == 1
        assert combinations(7, 6) == 7
        assert combinations(10, 6) == 210
        assert combinations(20, 6) == 38760

    def test_k_maior_que_n_devolve_zero(self) -> None:
        assert combinations(3, 5) == 0

    def test_valores_negativos_falham(self) -> None:
        with pytest.raises(ValidationError):
            combinations(-1, 2)


class TestCustoMegaSena:
    def test_aposta_minima(self) -> None:
        cost = preview_cost(Modality.MEGA_SENA, 6)
        assert cost.combinations == 1
        assert cost.total == Decimal("6.00")

    def test_sete_dezenas(self) -> None:
        cost = preview_cost(Modality.MEGA_SENA, 7)
        assert cost.combinations == 7
        assert cost.total == Decimal("42.00")

    def test_dez_dezenas_custa_mil_duzentos_e_sessenta(self) -> None:
        cost = preview_cost(Modality.MEGA_SENA, 10)
        assert cost.combinations == 210
        assert cost.total == Decimal("1260.00")

    def test_vinte_dezenas(self) -> None:
        cost = preview_cost(Modality.MEGA_SENA, 20)
        assert cost.combinations == 38760
        assert cost.total == Decimal("232560.00")

    def test_lote_de_cinco_volantes(self) -> None:
        unit, total = batch_cost(Modality.MEGA_SENA, 7, games=5)
        assert unit.total == Decimal("42.00")
        assert total == Decimal("210.00")


class TestCustoLotofacil:
    def test_aposta_minima(self) -> None:
        cost = preview_cost(Modality.LOTOFACIL, 15)
        assert cost.combinations == 1
        assert cost.total == Decimal("3.50")

    def test_dezesseis_dezenas(self) -> None:
        cost = preview_cost(Modality.LOTOFACIL, 16)
        assert cost.combinations == 16
        assert cost.total == Decimal("56.00")

    def test_vinte_dezenas(self) -> None:
        cost = preview_cost(Modality.LOTOFACIL, 20)
        assert cost.combinations == 15504
        assert cost.total == Decimal("54264.00")


class TestCustoQuina:
    def test_aposta_minima(self) -> None:
        cost = preview_cost(Modality.QUINA, 5)
        assert cost.combinations == 1
        assert cost.total == Decimal("3.00")

    def test_sete_dezenas(self) -> None:
        cost = preview_cost(Modality.QUINA, 7)
        assert cost.combinations == 21
        assert cost.total == Decimal("63.00")

    def test_quinze_dezenas(self) -> None:
        cost = preview_cost(Modality.QUINA, 15)
        assert cost.combinations == 3003
        assert cost.total == Decimal("9009.00")


class TestCustoDiaDeSorte:
    def test_aposta_minima_nao_multiplica_pelo_mes(self) -> None:
        cost = preview_cost(Modality.DIA_DE_SORTE, 7)
        assert cost.combinations == 1
        assert cost.total == Decimal("2.50")

    def test_oito_dezenas(self) -> None:
        cost = preview_cost(Modality.DIA_DE_SORTE, 8)
        assert cost.combinations == 8
        assert cost.total == Decimal("20.00")

    def test_quinze_dezenas(self) -> None:
        cost = preview_cost(Modality.DIA_DE_SORTE, 15)
        assert cost.combinations == 6435
        assert cost.total == Decimal("16087.50")


class TestCustoSuperSete:
    def test_aposta_minima(self) -> None:
        cost = preview_cost(Modality.SUPER_SETE, 7)
        assert cost.column_picks == (1, 1, 1, 1, 1, 1, 1)
        assert cost.combinations == 1
        assert cost.total == Decimal("3.00")

    def test_nove_numeros_geram_quatro_jogos(self) -> None:
        cost = preview_cost(Modality.SUPER_SETE, 9)
        assert cost.column_picks == (2, 2, 1, 1, 1, 1, 1)
        assert cost.combinations == 4
        assert cost.total == Decimal("12.00")

    def test_quatorze_numeros_geram_cento_e_vinte_e_oito_jogos(self) -> None:
        cost = preview_cost(Modality.SUPER_SETE, 14)
        assert cost.column_picks == (2, 2, 2, 2, 2, 2, 2)
        assert cost.combinations == 128

    def test_vinte_e_um_numeros_geram_o_maximo(self) -> None:
        cost = preview_cost(Modality.SUPER_SETE, 21)
        assert cost.column_picks == (3, 3, 3, 3, 3, 3, 3)
        assert cost.combinations == 2187
        assert cost.total == Decimal("6561.00")

    def test_distribuicao_explicita_muda_o_custo(self) -> None:
        cost = preview_cost(
            Modality.SUPER_SETE, 9, extras={"column_picks": [3, 1, 1, 1, 1, 1, 1]}
        )
        assert cost.combinations == 3
        assert cost.total == Decimal("9.00")

    def test_coluna_acima_do_maximo_falha(self) -> None:
        with pytest.raises(ValidationError):
            preview_cost(Modality.SUPER_SETE, 10, extras={"column_picks": [4, 1, 1, 1, 1, 1, 1]})

    def test_distribuicao_respeita_o_teto_por_coluna(self) -> None:
        assert distribute_columns(16, rule_for(Modality.SUPER_SETE)) == (3, 3, 2, 2, 2, 2, 2)


class TestLimitesDeEscolha:
    @pytest.mark.parametrize(
        ("modality", "abaixo", "acima"),
        [
            (Modality.MEGA_SENA, 5, 21),
            (Modality.LOTOFACIL, 14, 21),
            (Modality.QUINA, 4, 16),
            (Modality.DIA_DE_SORTE, 6, 16),
            (Modality.SUPER_SETE, 6, 22),
        ],
    )
    def test_fora_da_faixa_falha(self, modality: Modality, abaixo: int, acima: int) -> None:
        with pytest.raises(ValidationError):
            game_count(modality, abaixo)
        with pytest.raises(ValidationError):
            game_count(modality, acima)


class TestArredondamento:
    def test_round_half_up(self) -> None:
        assert money(Decimal("2.345")) == Decimal("2.35")
        assert money(Decimal("2.344")) == Decimal("2.34")
        assert money(Decimal("0.005")) == Decimal("0.01")


class TestVigenciaDePreco:
    def test_preco_antigo_da_mega(self) -> None:
        rule = rule_for(Modality.MEGA_SENA)
        assert rule.price_at(date(2024, 6, 1)) == Decimal("5.00")
        assert rule.price_at(date(2025, 6, 1)) == Decimal("6.00")
        assert rule.price_at() == Decimal("6.00")

    def test_custo_com_data_retroativa(self) -> None:
        cost = preview_cost(Modality.MEGA_SENA, 7, moment=date(2024, 6, 1))
        assert cost.total == Decimal("35.00")
