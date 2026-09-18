"""Acesso aos lotes gerados e aos jogos."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.entities import Game, GameBatch
from app.domain.enums import Modality, Profile
from app.infrastructure.db.models import GameBatchModel, GameModel


def _game_to_entity(model: GameModel) -> Game:
    return Game(
        id=model.id,
        game_batch_id=model.game_batch_id,
        numbers=tuple(model.numbers),
        extras=dict(model.extras or {}),
        engine_score=float(model.engine_score),
        already_drawn=model.already_drawn,
        matched_contests=tuple(model.matched_contests or ()),
    )


def _batch_to_entity(model: GameBatchModel) -> GameBatch:
    return GameBatch(
        id=model.id,
        modality=Modality(model.modality),
        created_at=model.created_at,
        profile=Profile(model.profile),
        seed=model.seed,
        numbers_per_game=model.numbers_per_game,
        games_count=model.games_count,
        total_cost=Decimal(model.total_cost),
        params=dict(model.params or {}),
        games=tuple(_game_to_entity(game) for game in model.games),
    )


class GameRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_batch(self, batch: GameBatch) -> GameBatchModel:
        batch_id = uuid.uuid4()
        model = GameBatchModel(
            id=batch_id,
            modality=batch.modality.value,
            profile=batch.profile.value,
            seed=batch.seed,
            numbers_per_game=batch.numbers_per_game,
            games_count=batch.games_count,
            total_cost=batch.total_cost,
            params=batch.params,
            games=[
                GameModel(
                    id=uuid.uuid4(),
                    game_batch_id=batch_id,
                    position=position,
                    numbers=list(game.numbers),
                    extras=game.extras,
                    engine_score=round(game.engine_score, 4),
                    already_drawn=game.already_drawn,
                    matched_contests=list(game.matched_contests),
                    metrics=game.metrics.as_dict() if game.metrics else {},
                )
                for position, game in enumerate(batch.games)
            ],
        )
        self._session.add(model)
        self._session.flush()
        return model

    def get_batch(self, batch_id: uuid.UUID) -> GameBatch | None:
        stmt = (
            select(GameBatchModel)
            .options(selectinload(GameBatchModel.games))
            .where(GameBatchModel.id == batch_id)
        )
        model = self._session.execute(stmt).scalars().first()
        return _batch_to_entity(model) if model else None

    def list_batches(self, modality: Modality | None = None, limit: int = 10) -> list[GameBatch]:
        stmt = select(GameBatchModel).options(selectinload(GameBatchModel.games))
        if modality is not None:
            stmt = stmt.where(GameBatchModel.modality == modality.value)
        stmt = stmt.order_by(GameBatchModel.created_at.desc()).limit(limit)
        return [_batch_to_entity(row) for row in self._session.execute(stmt).scalars()]

    def get_game(self, game_id: uuid.UUID) -> GameModel | None:
        stmt = (
            select(GameModel)
            .options(selectinload(GameModel.batch))
            .where(GameModel.id == game_id)
        )
        return self._session.execute(stmt).scalars().first()
