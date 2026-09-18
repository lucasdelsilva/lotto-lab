"""Concursos e importacao com substituicao total."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.application.dto.schemas import DrawResponse, ImportBatchResponse, PaginatedDraws
from app.application.use_cases.import_draws import import_draws
from app.core.errors import NotFoundError, ValidationError
from app.domain.enums import Modality
from app.infrastructure.db.session import get_db
from app.infrastructure.db.uow import UnitOfWork

router = APIRouter(prefix="/modalities/{modality}", tags=["draws"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post("/draws:import", status_code=201)
async def import_modality_draws(
    modality: Modality,
    file: Annotated[UploadFile, File(description="Planilha oficial .xlsx ou .csv")],
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Substitui todo o historico da modalidade enviada. As outras nao sao tocadas."""
    content = await file.read()
    if not content:
        raise ValidationError("Arquivo vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"Arquivo acima do limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    uow = UnitOfWork.from_session(session)
    summary = import_draws(uow, modality, file.filename or "upload.xlsx", content)
    return summary.as_dict()


@router.get("/draws", response_model=PaginatedDraws)
def list_draws(
    modality: Modality,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    contest_from: int | None = None,
    contest_to: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_db),
) -> PaginatedDraws:
    uow = UnitOfWork.from_session(session)
    rows, total = uow.draws.list_paginated(
        modality,
        limit=limit,
        offset=offset,
        contest_from=contest_from,
        contest_to=contest_to,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedDraws(
        items=[
            DrawResponse(
                contest_no=row.contest_no,
                drawn_at=row.drawn_at,
                numbers=list(row.numbers),
                extras=row.extras,
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/draws/latest", response_model=DrawResponse)
def latest_draw(modality: Modality, session: Session = Depends(get_db)) -> DrawResponse:
    uow = UnitOfWork.from_session(session)
    draw = uow.draws.latest(modality)
    if draw is None:
        raise NotFoundError(f"Nenhum concurso importado para {modality.label}.")
    return DrawResponse(
        contest_no=draw.contest_no,
        drawn_at=draw.drawn_at,
        numbers=list(draw.numbers),
        extras=draw.extras,
    )


@router.get("/import-batches", response_model=list[ImportBatchResponse])
def list_import_batches(
    modality: Modality,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_db),
) -> list[ImportBatchResponse]:
    uow = UnitOfWork.from_session(session)
    return [
        ImportBatchResponse(
            id=batch.id,  # type: ignore[arg-type]
            modality=batch.modality,
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
        for batch in uow.draws.list_batches(modality, limit)
    ]
