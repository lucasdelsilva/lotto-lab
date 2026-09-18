"""Importacao com substituicao total do historico de uma modalidade.

Regra central: o arquivo inteiro e lido e validado em memoria antes de qualquer escrita.
Se houver um unico erro de validacao, nada e apagado. Passando na validacao, o delete, o
insert em massa e o registro do lote acontecem na mesma transacao, e o escopo do delete e
sempre apenas a modalidade enviada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.logging import timed
from app.domain.entities import ImportBatch
from app.domain.enums import ImportStatus, Modality
from app.infrastructure.db.uow import UnitOfWork
from app.infrastructure.parsers.caixa_xlsx import ensure_valid, parse_file

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ImportSummary:
    batch_id: str
    modality: Modality
    filename: str
    file_hash: str
    rows_imported: int
    rows_deleted: int
    first_contest: int | None
    last_contest: int | None
    first_drawn_at: str | None
    last_drawn_at: str | None
    imported_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "modality": self.modality.value,
            "filename": self.filename,
            "file_hash": self.file_hash,
            "rows_imported": self.rows_imported,
            "rows_deleted": self.rows_deleted,
            "first_contest": self.first_contest,
            "last_contest": self.last_contest,
            "first_drawn_at": self.first_drawn_at,
            "last_drawn_at": self.last_drawn_at,
            "imported_at": self.imported_at,
        }


def import_draws(
    uow: UnitOfWork, modality: Modality, filename: str, content: bytes
) -> ImportSummary:
    with timed(logger, "import_draws", modality=modality.value, filename=filename) as context:
        parsed = parse_file(modality, filename, content)
        ensure_valid(parsed)
        context["rows"] = len(parsed.draws)

        # A partir daqui a transacao e unica: apaga, insere e registra o lote, ou nada acontece.
        deleted = uow.draws.delete_by_modality(modality)

        batch_model = uow.draws.add_batch(
            ImportBatch(
                modality=modality,
                filename=filename,
                file_hash=parsed.file_hash,
                rows_imported=len(parsed.draws),
                first_contest=parsed.first_contest,
                last_contest=parsed.last_contest,
                first_drawn_at=parsed.first_drawn_at,
                last_drawn_at=parsed.last_drawn_at,
                imported_at=datetime.now(UTC),
                status=ImportStatus.COMPLETED,
            )
        )

        inserted = uow.draws.bulk_insert(modality, parsed.draws, batch_model.id)
        uow.snapshots.invalidate(modality)
        uow.commit()

        context["deleted"] = deleted
        context["inserted"] = inserted

    return ImportSummary(
        batch_id=str(batch_model.id),
        modality=modality,
        filename=filename,
        file_hash=parsed.file_hash,
        rows_imported=inserted,
        rows_deleted=deleted,
        first_contest=parsed.first_contest,
        last_contest=parsed.last_contest,
        first_drawn_at=parsed.first_drawn_at.isoformat() if parsed.first_drawn_at else None,
        last_drawn_at=parsed.last_drawn_at.isoformat() if parsed.last_drawn_at else None,
        imported_at=batch_model.imported_at.isoformat()
        if batch_model.imported_at
        else datetime.now(UTC).isoformat(),
    )
