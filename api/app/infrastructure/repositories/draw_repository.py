"""Acesso aos concursos e aos lotes de importacao."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.domain.entities import Draw, ImportBatch
from app.domain.enums import ImportStatus, Modality
from app.infrastructure.db.models import DrawModel, ImportBatchModel


def _to_entity(model: DrawModel) -> Draw:
    return Draw(
        id=model.id,
        modality=Modality(model.modality),
        contest_no=model.contest_no,
        drawn_at=model.drawn_at,
        numbers=tuple(model.numbers),
        extras=dict(model.extras or {}),
        prize_tiers=model.prize_tiers,
        import_batch_id=model.import_batch_id,
    )


def _batch_to_entity(model: ImportBatchModel) -> ImportBatch:
    return ImportBatch(
        id=model.id,
        modality=Modality(model.modality),
        filename=model.filename,
        file_hash=model.file_hash,
        rows_imported=model.rows_imported,
        first_contest=model.first_contest,
        last_contest=model.last_contest,
        first_drawn_at=model.first_drawn_at,
        last_drawn_at=model.last_drawn_at,
        imported_at=model.imported_at,
        status=ImportStatus(model.status),
    )


class DrawRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count(self, modality: Modality) -> int:
        stmt = (
            select(func.count())
            .select_from(DrawModel)
            .where(DrawModel.modality == modality.value)
        )
        return int(self._session.execute(stmt).scalar_one())

    def list_all(self, modality: Modality) -> list[Draw]:
        """Historico completo em ordem crescente de concurso. Base de toda a analise."""
        stmt = (
            select(DrawModel)
            .where(DrawModel.modality == modality.value)
            .order_by(DrawModel.contest_no.asc())
        )
        return [_to_entity(row) for row in self._session.execute(stmt).scalars()]

    def list_paginated(
        self,
        modality: Modality,
        *,
        limit: int = 50,
        offset: int = 0,
        contest_from: int | None = None,
        contest_to: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Draw], int]:
        filters = [DrawModel.modality == modality.value]
        if contest_from is not None:
            filters.append(DrawModel.contest_no >= contest_from)
        if contest_to is not None:
            filters.append(DrawModel.contest_no <= contest_to)
        if date_from is not None:
            filters.append(DrawModel.drawn_at >= date_from)
        if date_to is not None:
            filters.append(DrawModel.drawn_at <= date_to)

        total = int(
            self._session.execute(
                select(func.count()).select_from(DrawModel).where(*filters)
            ).scalar_one()
        )
        stmt = (
            select(DrawModel)
            .where(*filters)
            .order_by(DrawModel.contest_no.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [_to_entity(row) for row in self._session.execute(stmt).scalars()]
        return rows, total

    def latest(self, modality: Modality) -> Draw | None:
        stmt = (
            select(DrawModel)
            .where(DrawModel.modality == modality.value)
            .order_by(DrawModel.contest_no.desc())
            .limit(1)
        )
        model = self._session.execute(stmt).scalars().first()
        return _to_entity(model) if model else None

    def by_contest(self, modality: Modality, contest_no: int) -> Draw | None:
        stmt = select(DrawModel).where(
            DrawModel.modality == modality.value, DrawModel.contest_no == contest_no
        )
        model = self._session.execute(stmt).scalars().first()
        return _to_entity(model) if model else None

    def delete_by_modality(self, modality: Modality) -> int:
        """Apaga somente o historico da modalidade informada."""
        result = self._session.execute(
            delete(DrawModel).where(DrawModel.modality == modality.value)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    def bulk_insert(self, modality: Modality, draws: Sequence[Draw], batch_id: uuid.UUID) -> int:
        payload = [
            {
                "id": uuid.uuid4(),
                "modality": modality.value,
                "contest_no": draw.contest_no,
                "drawn_at": draw.drawn_at,
                "numbers": list(draw.numbers),
                "extras": draw.extras,
                "prize_tiers": draw.prize_tiers,
                "import_batch_id": batch_id,
            }
            for draw in draws
        ]
        if payload:
            self._session.execute(insert(DrawModel), payload)
        return len(payload)

    def add_batch(self, batch: ImportBatch) -> ImportBatchModel:
        model = ImportBatchModel(
            id=uuid.uuid4(),
            modality=batch.modality.value,
            filename=batch.filename,
            file_hash=batch.file_hash,
            rows_imported=batch.rows_imported,
            first_contest=batch.first_contest,
            last_contest=batch.last_contest,
            first_drawn_at=batch.first_drawn_at,
            last_drawn_at=batch.last_drawn_at,
            imported_at=batch.imported_at,
            status=batch.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return model

    def list_batches(self, modality: Modality, limit: int = 20) -> list[ImportBatch]:
        stmt = (
            select(ImportBatchModel)
            .where(ImportBatchModel.modality == modality.value)
            .order_by(ImportBatchModel.imported_at.desc())
            .limit(limit)
        )
        return [_batch_to_entity(row) for row in self._session.execute(stmt).scalars()]
