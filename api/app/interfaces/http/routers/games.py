"""Geracao de jogos, consulta de lote, insight e revisao pela IA."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.dto.schemas import (
    CostSummary,
    GameSummary,
    GenerateGamesRequest,
    GenerateGamesResponse,
)
from app.application.use_cases.ai_advisor import review_batch
from app.application.use_cases.explain_game import explain_game
from app.application.use_cases.generate_games import generate_games
from app.core.errors import NotFoundError
from app.domain.enums import Modality
from app.infrastructure.db.session import get_db
from app.infrastructure.db.uow import UnitOfWork

router = APIRouter(tags=["games"])


@router.post(
    "/modalities/{modality}/games:generate",
    response_model=GenerateGamesResponse,
    status_code=201,
)
def generate(
    modality: Modality,
    request: GenerateGamesRequest,
    session: Session = Depends(get_db),
) -> GenerateGamesResponse:
    """Resposta enxuta por contrato: dezenas, marca de ja sorteado e custo, nada alem."""
    output = generate_games(UnitOfWork.from_session(session), modality, request)
    return GenerateGamesResponse(
        batch_id=uuid.UUID(output.batch_id),
        modality=output.modality,
        seed=output.seed,
        games=[
            GameSummary(
                id=uuid.UUID(game["id"]),
                numbers=game["numbers"],
                already_drawn=game["already_drawn"],
                extras=game["extras"],
            )
            for game in output.games
        ],
        cost=CostSummary(
            per_game=output.per_game_cost,
            total=output.total_cost,
            within_budget=output.within_budget,
        ),
    )


@router.get("/game-batches/{batch_id}")
def get_batch(batch_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    uow = UnitOfWork.from_session(session)
    batch = uow.games.get_batch(batch_id)
    if batch is None:
        raise NotFoundError(f"Lote {batch_id} nao encontrado.")
    return {
        "batch_id": str(batch.id),
        "modality": batch.modality.value,
        "created_at": batch.created_at.isoformat(),
        "profile": batch.profile.value,
        "seed": batch.seed,
        "numbers_per_game": batch.numbers_per_game,
        "games_count": batch.games_count,
        "total_cost": str(batch.total_cost),
        "params": batch.params,
        "games": [
            {
                "id": str(game.id),
                "numbers": list(game.numbers),
                "already_drawn": game.already_drawn,
                "matched_contests": list(game.matched_contests),
                "engine_score": game.engine_score,
            }
            for game in batch.games
        ],
    }


@router.get("/game-batches")
def list_batches(
    modality: Modality | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    session: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    uow = UnitOfWork.from_session(session)
    return [
        {
            "batch_id": str(batch.id),
            "modality": batch.modality.value,
            "created_at": batch.created_at.isoformat(),
            "profile": batch.profile.value,
            "games_count": batch.games_count,
            "numbers_per_game": batch.numbers_per_game,
            "total_cost": str(batch.total_cost),
        }
        for batch in uow.games.list_batches(modality, limit)
    ]


@router.get("/games/{game_id}/insight")
def game_insight(game_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    """Detalhamento sob demanda. Nunca faz parte da resposta da geracao."""
    return explain_game(UnitOfWork.from_session(session), game_id)


@router.post("/games/{game_id}/ai-review")
def ai_review(game_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    """Curadoria da IA sobre o lote ao qual o jogo pertence."""
    uow = UnitOfWork.from_session(session)
    game = uow.games.get_game(game_id)
    if game is None:
        raise NotFoundError(f"Jogo {game_id} nao encontrado.")
    return review_batch(uow, game.game_batch_id)


@router.post("/game-batches/{batch_id}/ai-review")
def ai_review_batch(batch_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    return review_batch(UnitOfWork.from_session(session), batch_id)
