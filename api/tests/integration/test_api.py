"""Teste ponta a ponta pela borda HTTP: importar, analisar, gerar, apostar e conferir."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.enums import Modality
from app.infrastructure.db.session import get_db
from app.main import create_app
from tests.integration.test_parser import build_xlsx

MEGA_HEADER = ["Concurso", "Data do Sorteio", "Bola1", "Bola2", "Bola3", "Bola4", "Bola5", "Bola6"]


def mega_file(draws_count: int = 250) -> bytes:
    """Historico sintetico grande o bastante para as faixas historicas fazerem sentido."""
    rng = np.random.default_rng(2024)
    rows = []
    for index in range(draws_count):
        numbers = sorted(rng.choice(np.arange(1, 61), size=6, replace=False).tolist())
        day = (index % 28) + 1
        month = (index % 12) + 1
        rows.append([index + 1, f"{day:02d}/{month:02d}/2020", *numbers])
    return build_xlsx(MEGA_HEADER, rows)


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    # Sem chave da OpenAI a aplicacao continua utilizavel.
    assert "ai_available" in body


def test_preview_de_custo(client: TestClient) -> None:
    response = client.get("/api/modalities/MEGA_SENA/pricing/preview", params={"n": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["combinations"] == 210
    assert body["per_game"] == "1260.00"


def test_preview_recusa_quantidade_invalida(client: TestClient) -> None:
    response = client.get("/api/modalities/MEGA_SENA/pricing/preview", params={"n": 21})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_fluxo_completo(client: TestClient) -> None:
    # 1. Importar
    upload = client.post(
        "/api/modalities/MEGA_SENA/draws:import",
        files={"file": ("mega.xlsx", mega_file(), "application/vnd.ms-excel")},
    )
    assert upload.status_code == 201
    assert upload.json()["rows_imported"] == 250

    # 2. Analisar
    analysis = client.get("/api/modalities/MEGA_SENA/analysis")
    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload["history_meta"]["total_draws"] == 250
    assert len(payload["numbers"]) == 60
    assert payload["cached"] is False

    cached = client.get("/api/modalities/MEGA_SENA/analysis").json()
    assert cached["cached"] is True

    # 3. Gerar, com resposta enxuta
    generation = client.post(
        "/api/modalities/MEGA_SENA/games:generate",
        json={"numbers_per_game": 7, "games": 3, "profile": "balanced", "seed": 42},
    )
    assert generation.status_code == 201
    batch = generation.json()
    assert batch["seed"] == 42
    assert len(batch["games"]) == 3
    assert batch["cost"]["per_game"] == "42.00"
    assert batch["cost"]["total"] == "126.00"

    for game in batch["games"]:
        assert set(game) == {"id", "numbers", "already_drawn", "extras"}
        assert len(game["numbers"]) == 7
        assert all(1 <= number <= 60 for number in game["numbers"])

    # 4. Mesma seed, mesmo resultado
    repetida = client.post(
        "/api/modalities/MEGA_SENA/games:generate",
        json={"numbers_per_game": 7, "games": 3, "profile": "balanced", "seed": 42},
    ).json()
    assert [game["numbers"] for game in repetida["games"]] == [
        game["numbers"] for game in batch["games"]
    ]

    # 5. Insight sob demanda
    game_id = batch["games"][0]["id"]
    insight = client.get(f"/api/games/{game_id}/insight")
    assert insight.status_code == 200
    detail = insight.json()
    assert detail["metrics"]["sum"] == sum(batch["games"][0]["numbers"])
    assert "pattern_ranges" in detail
    assert "best_historical_match" in detail

    # 6. Registrar e conferir aposta
    bet = client.post("/api/bets", json={"game_id": game_id, "contest_no": 1})
    assert bet.status_code == 201
    assert Decimal(bet.json()["cost"]) == Decimal("42.00")

    check = client.post("/api/bets:check", json={"modality": "MEGA_SENA"})
    assert check.status_code == 200
    assert check.json()["checked"] == 1
    conferida = check.json()["results"][0]
    assert conferida["status"] == "CHECKED"
    assert conferida["result"]["hits"] >= 0

    # 7. Resumo financeiro
    summary = client.get("/api/bets/summary").json()
    assert Decimal(summary["total_spent"]) == Decimal("42.00")
    assert Decimal(summary["balance"]) == Decimal("-42.00")


def test_geracao_respeita_o_orcamento(client: TestClient) -> None:
    client.post(
        "/api/modalities/MEGA_SENA/draws:import",
        files={"file": ("mega.xlsx", mega_file(), "application/vnd.ms-excel")},
    )

    response = client.post(
        "/api/modalities/MEGA_SENA/games:generate",
        json={"numbers_per_game": 10, "games": 5, "seed": 1, "budget_limit": 100},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "budget_exceeded"
    assert body["total_cost"] == "6300.00"


def test_geracao_sem_historico(client: TestClient) -> None:
    response = client.post(
        "/api/modalities/QUINA/games:generate", json={"numbers_per_game": 5, "games": 1}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_import_invalido_devolve_erros_por_linha(client: TestClient) -> None:
    ruim = build_xlsx(MEGA_HEADER, [[1, "11/03/1996", 4, 5, 30, 33, 41, 99]])
    response = client.post(
        "/api/modalities/MEGA_SENA/draws:import",
        files={"file": ("ruim.xlsx", ruim, "application/vnd.ms-excel")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "import_validation_error"
    assert body["errors"][0]["row"] == 2
    assert "99" in body["errors"][0]["value"]


def test_revisao_da_ia_degrada_sem_chave(client: TestClient) -> None:
    client.post(
        "/api/modalities/MEGA_SENA/draws:import",
        files={"file": ("mega.xlsx", mega_file(), "application/vnd.ms-excel")},
    )
    batch = client.post(
        "/api/modalities/MEGA_SENA/games:generate",
        json={"numbers_per_game": 6, "games": 2, "seed": 3},
    ).json()

    response = client.post(f"/api/game-batches/{batch['batch_id']}/ai-review")

    assert response.status_code == 200
    body = response.json()
    assert body["ai_available"] is False
    assert body["analysis"] is None
    assert "OpenAI" in (body["error"] or "")


def test_lote_completo_traz_o_detalhe(client: TestClient) -> None:
    client.post(
        "/api/modalities/MEGA_SENA/draws:import",
        files={"file": ("mega.xlsx", mega_file(), "application/vnd.ms-excel")},
    )
    batch = client.post(
        "/api/modalities/MEGA_SENA/games:generate",
        json={"numbers_per_game": 6, "games": 2, "seed": 5},
    ).json()

    response = client.get(f"/api/game-batches/{batch['batch_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["games_count"] == 2
    assert body["params"]["weights"]["freq"] == 0.25
    assert Modality(body["modality"]) is Modality.MEGA_SENA


class TestApostaManual:
    """Registro de aposta ja paga na loteria, sem passar pelo gerador."""

    def test_registra_informando_modalidade_numeros_e_concurso(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={
                "modality": "MEGA_SENA",
                "contest_no": 3058,
                "numbers": [5, 14, 18, 28, 32, 47],
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["game_id"] is None  # e o que marca a aposta como manual na tela
        assert body["numbers"] == [5, 14, 18, 28, 32, 47]
        assert Decimal(body["cost"]) == Decimal("6.00")  # calculado pela tabela oficial
        assert body["status"] == "PENDING"

    def test_calcula_o_custo_de_volante_maior(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={
                "modality": "MEGA_SENA",
                "contest_no": 3058,
                "numbers": [1, 5, 14, 18, 28, 32, 47],
            },
        )

        assert Decimal(response.json()["cost"]) == Decimal("42.00")

    def test_aceita_valor_pago_diferente_do_calculado(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={
                "modality": "MEGA_SENA",
                "contest_no": 3058,
                "numbers": [5, 14, 18, 28, 32, 47],
                "cost": "7.50",
            },
        )

        assert Decimal(response.json()["cost"]) == Decimal("7.50")

    def test_guarda_o_mes_do_dia_de_sorte(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={
                "modality": "DIA_DE_SORTE",
                "contest_no": 1300,
                "numbers": [3, 7, 11, 17, 21, 25, 31],
                "extras": {"month": 9},
            },
        )

        assert response.status_code == 201
        assert response.json()["extras"] == {"month": 9}

    def test_guarda_as_colunas_do_super_sete(self, client: TestClient) -> None:
        colunas = [[1], [2], [3], [4], [5], [6], [7]]
        response = client.post(
            "/api/bets",
            json={
                "modality": "SUPER_SETE",
                "contest_no": 900,
                "numbers": [1, 2, 3, 4, 5, 6, 7],
                "extras": {"columns": colunas},
            },
        )

        assert response.status_code == 201
        assert response.json()["extras"]["columns"] == colunas

    def test_recusa_dezena_fora_do_universo(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={"modality": "MEGA_SENA", "contest_no": 3058, "numbers": [5, 14, 18, 28, 32, 99]},
        )

        assert response.status_code == 422
        assert "fora do universo" in response.json()["detail"]

    def test_recusa_dezena_repetida(self, client: TestClient) -> None:
        response = client.post(
            "/api/bets",
            json={"modality": "MEGA_SENA", "contest_no": 3058, "numbers": [5, 5, 18, 28, 32, 47]},
        )

        assert response.status_code == 422
        assert "repetidas" in response.json()["detail"]

    def test_recusa_pedido_sem_modalidade_nem_jogo(self, client: TestClient) -> None:
        response = client.post("/api/bets", json={"contest_no": 3058})

        assert response.status_code == 422

    def test_remove_a_aposta(self, client: TestClient) -> None:
        criada = client.post(
            "/api/bets",
            json={"modality": "MEGA_SENA", "contest_no": 3058, "numbers": [5, 14, 18, 28, 32, 47]},
        ).json()

        assert client.get("/api/bets").json()["total"] == 1

        apagada = client.delete(f"/api/bets/{criada['id']}")

        assert apagada.status_code == 204
        assert client.get("/api/bets").json()["total"] == 0
        assert client.get(f"/api/bets/{criada['id']}").status_code == 404

    def test_remover_aposta_inexistente_da_404(self, client: TestClient) -> None:
        response = client.delete("/api/bets/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404

    def test_aposta_manual_entra_na_conferencia(self, client: TestClient) -> None:
        client.post(
            "/api/modalities/MEGA_SENA/draws:import",
            files={"file": ("mega.xlsx", mega_file(), "application/vnd.ms-excel")},
        )
        sorteado = client.get("/api/modalities/MEGA_SENA/draws/latest").json()

        # Aposta identica ao concurso sorteado: precisa fechar com acerto cheio.
        client.post(
            "/api/bets",
            json={
                "modality": "MEGA_SENA",
                "contest_no": sorteado["contest_no"],
                "numbers": sorteado["numbers"],
            },
        )
        conferencia = client.post("/api/bets:check", json={"modality": "MEGA_SENA"}).json()

        assert conferencia["checked"] == 1
        assert conferencia["results"][0]["result"]["hits"] == 6
