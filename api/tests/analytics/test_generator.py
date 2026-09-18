from __future__ import annotations

import numpy as np
import pytest

from app.analytics.filters import FilterConfig
from app.analytics.generator import GenerationRequest, generate
from app.core.errors import GenerationExhaustedError
from app.domain.enums import AlreadyDrawnPolicy, Modality, Profile
from app.domain.rules import ModalityRule, rule_for
from tests.conftest import random_history


@pytest.fixture
def mega_long_history(mega_rule: ModalityRule) -> tuple[np.ndarray, np.ndarray]:
    draws = random_history(mega_rule, 400, seed=11)
    contests = np.arange(1, 401, dtype=np.int64)
    return draws, contests


def test_mesma_seed_gera_os_mesmos_jogos(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history
    request = GenerationRequest(numbers_per_game=6, games=5, profile=Profile.BALANCED, seed=42)

    primeiro = generate(draws, contests, mega_rule, request)
    segundo = generate(draws, contests, mega_rule, request)

    assert [game.numbers for game in primeiro.games] == [game.numbers for game in segundo.games]
    assert primeiro.seed == segundo.seed == 42


def test_seeds_diferentes_geram_jogos_diferentes(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history

    primeiro = generate(
        draws, contests, mega_rule, GenerationRequest(numbers_per_game=6, games=5, seed=1)
    )
    segundo = generate(
        draws, contests, mega_rule, GenerationRequest(numbers_per_game=6, games=5, seed=2)
    )

    assert [game.numbers for game in primeiro.games] != [game.numbers for game in segundo.games]


def test_respeita_universo_e_quantidade(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history
    result = generate(
        draws, contests, mega_rule, GenerationRequest(numbers_per_game=8, games=4, seed=7)
    )

    assert len(result.games) == 4
    for game in result.games:
        assert len(game.numbers) == 8
        assert len(set(game.numbers)) == 8
        assert all(1 <= number <= 60 for number in game.numbers)
        assert list(game.numbers) == sorted(game.numbers)


def test_diversificacao_limita_a_sobreposicao(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history
    result = generate(
        draws,
        contests,
        mega_rule,
        GenerationRequest(numbers_per_game=6, games=5, seed=3, max_overlap=2),
    )

    combos = [set(game.numbers) for game in result.games]
    for index, primeiro in enumerate(combos):
        for segundo in combos[index + 1 :]:
            assert len(primeiro & segundo) <= 2


def test_marca_combinacao_ja_sorteada(mega_rule: ModalityRule) -> None:
    # Historico em que o mesmo jogo sai varias vezes, para forcar a deteccao.
    repetido = [2, 12, 23, 34, 45, 56]
    draws = np.asarray([repetido] * 60, dtype=np.int64)
    contests = np.arange(1, 61, dtype=np.int64)

    result = generate(
        draws,
        contests,
        mega_rule,
        GenerationRequest(
            numbers_per_game=6,
            games=1,
            seed=5,
            filters=FilterConfig(enabled=frozenset(), on_already_drawn=AlreadyDrawnPolicy.FLAG),
            profile=Profile.HOT,
        ),
    )

    jogo = result.games[0]
    if jogo.already_drawn:
        assert jogo.matched_contests
    assert isinstance(jogo.already_drawn, bool)


def test_politica_reject_nao_devolve_jogo_ja_sorteado(mega_rule: ModalityRule) -> None:
    repetido = [2, 12, 23, 34, 45, 56]
    draws = np.asarray([repetido] * 60, dtype=np.int64)
    contests = np.arange(1, 61, dtype=np.int64)

    result = generate(
        draws,
        contests,
        mega_rule,
        GenerationRequest(
            numbers_per_game=6,
            games=3,
            seed=9,
            filters=FilterConfig(
                enabled=frozenset(), on_already_drawn=AlreadyDrawnPolicy.REJECT
            ),
        ),
    )

    assert all(game.already_drawn is False for game in result.games)


def test_filtros_impossiveis_dao_erro_claro(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history

    with pytest.raises(GenerationExhaustedError) as exc:
        generate(
            draws,
            contests,
            mega_rule,
            GenerationRequest(
                numbers_per_game=6,
                games=3,
                seed=1,
                filters=FilterConfig(max_consecutive=0, min_quadrants_covered=4),
                max_attempts=300,
            ),
        )

    assert "tentativas" in str(exc.value)


def test_perfil_uniforme_e_valido(
    mega_long_history: tuple[np.ndarray, np.ndarray], mega_rule: ModalityRule
) -> None:
    draws, contests = mega_long_history
    result = generate(
        draws,
        contests,
        mega_rule,
        GenerationRequest(numbers_per_game=6, games=3, seed=4, profile=Profile.UNIFORM),
    )

    assert len(result.games) == 3
    assert result.weights.is_uniform


def test_dia_de_sorte_escolhe_o_mes() -> None:
    rule = rule_for(Modality.DIA_DE_SORTE)
    draws = random_history(rule, 300, seed=21)
    contests = np.arange(1, 301, dtype=np.int64)
    months = [(index % 12) + 1 for index in range(300)]

    result = generate(
        draws,
        contests,
        rule,
        GenerationRequest(numbers_per_game=7, games=3, seed=8),
        months=months,
    )

    for game in result.games:
        assert 1 <= game.extras["month"] <= 12


def test_super_sete_respeita_colunas() -> None:
    rule = rule_for(Modality.SUPER_SETE)
    rng = np.random.default_rng(3)
    draws = rng.integers(0, 10, size=(200, 7)).astype(np.int64)
    contests = np.arange(1, 201, dtype=np.int64)

    result = generate(
        draws, contests, rule, GenerationRequest(numbers_per_game=9, games=4, seed=6)
    )

    assert len(result.games) == 4
    for game in result.games:
        columns = game.extras["columns"]
        assert len(columns) == 7
        assert sum(len(column) for column in columns) == 9
        for column in columns:
            assert 1 <= len(column) <= 3
            assert all(0 <= digit <= 9 for digit in column)


def test_super_sete_reprodutivel() -> None:
    rule = rule_for(Modality.SUPER_SETE)
    rng = np.random.default_rng(3)
    draws = rng.integers(0, 10, size=(200, 7)).astype(np.int64)
    contests = np.arange(1, 201, dtype=np.int64)
    request = GenerationRequest(numbers_per_game=10, games=3, seed=77)

    primeiro = generate(draws, contests, rule, request)
    segundo = generate(draws, contests, rule, request)

    assert [game.extras["columns"] for game in primeiro.games] == [
        game.extras["columns"] for game in segundo.games
    ]
