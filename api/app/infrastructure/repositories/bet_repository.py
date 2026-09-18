"""Acesso as apostas registradas e aos resultados conferidos."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import BetStatus, Modality
from app.infrastructure.db.models import BetModel, BetResultModel


class BetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        modality: Modality,
        contest_no: int,
        numbers: Sequence[int],
        extras: dict[str, Any],
        cost: Decimal,
        game_id: uuid.UUID | None,
        placed_at: datetime,
    ) -> BetModel:
        model = BetModel(
            id=uuid.uuid4(),
            game_id=game_id,
            modality=modality.value,
            contest_no=contest_no,
            numbers=list(numbers),
            extras=extras,
            cost=cost,
            placed_at=placed_at,
            status=BetStatus.PENDING.value,
        )
        self._session.add(model)
        self._session.flush()
        return model

    def get(self, bet_id: uuid.UUID) -> BetModel | None:
        stmt = (
            select(BetModel).options(selectinload(BetModel.result)).where(BetModel.id == bet_id)
        )
        return self._session.execute(stmt).scalars().first()

    def search(
        self,
        *,
        modality: Modality | None = None,
        status: BetStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[BetModel], int]:
        filters = []
        if modality is not None:
            filters.append(BetModel.modality == modality.value)
        if status is not None:
            filters.append(BetModel.status == status.value)
        if date_from is not None:
            filters.append(func.date(BetModel.placed_at) >= date_from)
        if date_to is not None:
            filters.append(func.date(BetModel.placed_at) <= date_to)

        total = int(
            self._session.execute(
                select(func.count()).select_from(BetModel).where(*filters)
            ).scalar_one()
        )
        stmt = (
            select(BetModel)
            .options(selectinload(BetModel.result))
            .where(*filters)
            .order_by(BetModel.placed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars()), total

    def delete(self, bet: BetModel) -> None:
        """Remove a aposta e o resultado conferido junto, pelo cascade do relacionamento."""
        self._session.delete(bet)
        self._session.flush()

    def list_pending(self, modality: Modality | None = None) -> list[BetModel]:
        filters = [BetModel.status == BetStatus.PENDING.value]
        if modality is not None:
            filters.append(BetModel.modality == modality.value)
        stmt = select(BetModel).options(selectinload(BetModel.result)).where(*filters)
        return list(self._session.execute(stmt).scalars())

    def upsert_result(
        self,
        bet: BetModel,
        *,
        hits: int,
        extra_hit: bool,
        prize: Decimal,
        checked_at: datetime,
    ) -> BetResultModel:
        result = bet.result
        if result is None:
            result = BetResultModel(id=uuid.uuid4(), bet_id=bet.id)
            # Ligar pelo relacionamento, e nao so pela chave, para que a aposta ja carregada
            # em memoria enxergue o resultado sem precisar de um novo select.
            bet.result = result
            self._session.add(result)
        result.hits = hits
        result.extra_hit = extra_hit
        result.prize = prize
        result.checked_at = checked_at
        bet.status = BetStatus.CHECKED.value
        self._session.flush()
        return result

    def summary(self) -> list[dict[str, Any]]:
        """Gasto e retorno agregados por modalidade e por mes."""
        month = func.to_char(BetModel.placed_at, "YYYY-MM").label("month")
        stmt = (
            select(
                BetModel.modality,
                month,
                func.count(BetModel.id).label("bets"),
                func.coalesce(func.sum(BetModel.cost), 0).label("spent"),
                func.coalesce(func.sum(BetResultModel.prize), 0).label("returned"),
            )
            .join(BetResultModel, BetResultModel.bet_id == BetModel.id, isouter=True)
            .group_by(BetModel.modality, month)
            .order_by(month.desc(), BetModel.modality)
        )
        rows = self._session.execute(stmt).all()
        return [
            {
                "modality": row.modality,
                "month": row.month,
                "bets": int(row.bets),
                "spent": Decimal(row.spent),
                "returned": Decimal(row.returned),
                "balance": Decimal(row.returned) - Decimal(row.spent),
            }
            for row in rows
        ]
