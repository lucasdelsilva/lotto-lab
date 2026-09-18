"""Cache do snapshot de analise, invalidado a cada importacao."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import Modality
from app.infrastructure.db.models import AnalysisSnapshotModel


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, modality: Modality) -> AnalysisSnapshotModel | None:
        stmt = select(AnalysisSnapshotModel).where(
            AnalysisSnapshotModel.modality == modality.value
        )
        return self._session.execute(stmt).scalars().first()

    def get_fresh(self, modality: Modality, history_hash: str) -> dict[str, Any] | None:
        """Devolve o payload apenas se o historico nao mudou desde o calculo."""
        model = self.get(modality)
        if model is None or model.history_hash != history_hash:
            return None
        return dict(model.payload)

    def save(
        self,
        modality: Modality,
        *,
        history_hash: str,
        draws_count: int,
        payload: dict[str, Any],
    ) -> AnalysisSnapshotModel:
        model = self.get(modality)
        if model is None:
            model = AnalysisSnapshotModel(id=uuid.uuid4(), modality=modality.value)
            self._session.add(model)
        model.history_hash = history_hash
        model.draws_count = draws_count
        model.payload = payload
        model.computed_at = datetime.now(UTC)
        self._session.flush()
        return model

    def invalidate(self, modality: Modality) -> None:
        self._session.execute(
            delete(AnalysisSnapshotModel).where(AnalysisSnapshotModel.modality == modality.value)
        )
