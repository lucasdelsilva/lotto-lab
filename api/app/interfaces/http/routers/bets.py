"""Apostas, conferencia e resumo financeiro."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.dto.schemas import (
    BetResponse,
    BetResultResponse,
    BetsSummary,
    CheckBetsRequest,
    CheckBetsResponse,
    CreateBetRequest,
    PaginatedBets,
    SummaryRow,
)
from app.application.use_cases.bets import bets_summary, check_bets, create_bet
from app.core.errors import NotFoundError
from app.domain.enums import BetStatus, Modality
from app.infrastructure.db.models import BetModel
from app.infrastructure.db.session import get_db
from app.infrastructure.db.uow import UnitOfWork

router = APIRouter(prefix="/bets", tags=["bets"])


def _to_response(bet: BetModel) -> BetResponse:
    return BetResponse(
        id=bet.id,
        game_id=bet.game_id,
        modality=Modality(bet.modality),
        contest_no=bet.contest_no,
        numbers=list(bet.numbers),
        extras=dict(bet.extras or {}),
        cost=bet.cost,
        placed_at=bet.placed_at,
        status=BetStatus(bet.status),
        result=BetResultResponse(
            hits=bet.result.hits,
            extra_hit=bet.result.extra_hit,
            prize=bet.result.prize,
            checked_at=bet.result.checked_at,
        )
        if bet.result
        else None,
    )


@router.post("", response_model=BetResponse, status_code=201)
def register_bet(request: CreateBetRequest, session: Session = Depends(get_db)) -> BetResponse:
    uow = UnitOfWork.from_session(session)
    bet = create_bet(uow, request)
    uow.commit()
    return _to_response(bet)


@router.get("", response_model=PaginatedBets)
def list_bets(
    modality: Modality | None = None,
    status: BetStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Session = Depends(get_db),
) -> PaginatedBets:
    uow = UnitOfWork.from_session(session)
    rows, total = uow.bets.search(
        modality=modality,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return PaginatedBets(
        items=[_to_response(bet) for bet in rows], total=total, limit=limit, offset=offset
    )


@router.get("/summary", response_model=BetsSummary)
def summary(session: Session = Depends(get_db)) -> BetsSummary:
    data = bets_summary(UnitOfWork.from_session(session))
    return BetsSummary(
        rows=[
            SummaryRow(
                modality=Modality(row["modality"]),
                month=row["month"],
                bets=row["bets"],
                spent=row["spent"],
                returned=row["returned"],
                balance=row["balance"],
            )
            for row in data["rows"]
        ],
        total_spent=data["total_spent"],
        total_returned=data["total_returned"],
        balance=data["balance"],
    )


@router.post(":check", response_model=CheckBetsResponse)
def check(
    request: CheckBetsRequest | None = None, session: Session = Depends(get_db)
) -> CheckBetsResponse:
    """Confere as apostas pendentes contra os concursos ja importados."""
    uow = UnitOfWork.from_session(session)
    outcome = check_bets(uow, request.modality if request else None)
    return CheckBetsResponse(
        checked=outcome["checked"],
        skipped=outcome["skipped"],
        results=[_to_response(bet) for bet in outcome["bets"]],
    )


@router.get("/{bet_id}", response_model=BetResponse)
def get_bet(bet_id: uuid.UUID, session: Session = Depends(get_db)) -> BetResponse:
    uow = UnitOfWork.from_session(session)
    bet = uow.bets.get(bet_id)
    if bet is None:
        raise NotFoundError(f"Aposta {bet_id} nao encontrada.")
    return _to_response(bet)


@router.delete("/{bet_id}", status_code=204)
def delete_bet(bet_id: uuid.UUID, session: Session = Depends(get_db)) -> None:
    """Remove uma aposta registrada. Util para corrigir digitacao no registro manual."""
    uow = UnitOfWork.from_session(session)
    bet = uow.bets.get(bet_id)
    if bet is None:
        raise NotFoundError(f"Aposta {bet_id} nao encontrada.")
    uow.bets.delete(bet)
    uow.commit()
