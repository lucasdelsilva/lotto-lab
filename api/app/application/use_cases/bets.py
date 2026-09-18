"""Registro, conferencia e resumo financeiro das apostas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.application.dto.schemas import CreateBetRequest
from app.core.errors import NotFoundError, ValidationError
from app.domain.enums import Modality
from app.domain.pricing import money, preview_cost
from app.domain.rules import rule_for
from app.infrastructure.db.models import BetModel
from app.infrastructure.db.uow import UnitOfWork


def create_bet(uow: UnitOfWork, request: CreateBetRequest) -> BetModel:
    """Registra uma aposta, seja a partir de um jogo gerado, seja digitada a mao."""
    numbers: list[int]
    extras: dict[str, Any] = dict(request.extras)
    game_id: uuid.UUID | None = None
    modality: Modality

    if request.game_id is not None:
        game = uow.games.get_game(request.game_id)
        if game is None:
            raise NotFoundError(f"Jogo {request.game_id} nao encontrado.")
        game_id = game.id
        modality = Modality(game.batch.modality)
        numbers = list(game.numbers)
        stored = dict(game.extras or {})
        for key in ("columns", "month"):
            if key in stored and key not in extras:
                extras[key] = stored[key]
    else:
        if request.modality is None or not request.numbers:
            raise ValidationError(
                "Informe game_id, ou entao modality e numbers para registrar a aposta."
            )
        modality = request.modality
        numbers = list(request.numbers)

    rule = rule_for(modality)
    if not rule.is_column_based:
        invalid = [number for number in numbers if not rule.contains(number)]
        if invalid:
            raise ValidationError(
                f"Dezenas fora do universo de {modality.label}: {invalid}."
            )
        if len(set(numbers)) != len(numbers):
            raise ValidationError("A aposta tem dezenas repetidas.")

    cost = request.cost
    if cost is None:
        extras_for_cost = (
            {"column_picks": [len(column) for column in extras["columns"]]}
            if rule.is_column_based and "columns" in extras
            else None
        )
        cost = preview_cost(modality, len(numbers), extras_for_cost).total

    return uow.bets.add(
        modality=modality,
        contest_no=request.contest_no,
        numbers=numbers,
        extras=extras,
        cost=money(Decimal(cost)),
        game_id=game_id,
        placed_at=datetime.now(UTC),
    )


def _hits_for(
    bet: BetModel, drawn_numbers: list[int], drawn_extras: dict[str, Any]
) -> tuple[int, bool]:
    modality = Modality(bet.modality)
    rule = rule_for(modality)

    if rule.is_column_based:
        columns = bet.extras.get("columns") or []
        drawn_columns = drawn_extras.get("columns") or drawn_numbers
        hits = sum(
            1
            for index, digit in enumerate(drawn_columns)
            if index < len(columns) and digit in columns[index]
        )
        return hits, False

    hits = len(set(bet.numbers) & set(drawn_numbers))
    extra_hit = False
    if modality is Modality.DIA_DE_SORTE:
        extra_hit = bet.extras.get("month") is not None and bet.extras.get(
            "month"
        ) == drawn_extras.get("month")
    return hits, extra_hit


def _prize_for(hits: int, extra_hit: bool, prize_tiers: dict[str, Any] | None) -> Decimal:
    """O premio so e conhecido quando a planilha importada traz a faixa de premiacao.

    Sem essa informacao a aposta e conferida do mesmo jeito, com premio zero, e o painel
    mostra apenas os acertos.
    """
    if not prize_tiers:
        return Decimal("0.00")
    key = f"{hits}+mes" if extra_hit and f"{hits}+mes" in prize_tiers else str(hits)
    value = prize_tiers.get(key)
    return money(Decimal(str(value))) if value is not None else Decimal("0.00")


def check_bets(uow: UnitOfWork, modality: Modality | None = None) -> dict[str, Any]:
    """Confere as apostas pendentes contra os concursos ja importados."""
    pending = uow.bets.list_pending(modality)
    checked: list[BetModel] = []
    skipped = 0

    for bet in pending:
        draw = uow.draws.by_contest(Modality(bet.modality), bet.contest_no)
        if draw is None:
            skipped += 1
            continue
        hits, extra_hit = _hits_for(bet, list(draw.numbers), draw.extras)
        uow.bets.upsert_result(
            bet,
            hits=hits,
            extra_hit=extra_hit,
            prize=_prize_for(hits, extra_hit, draw.prize_tiers),
            checked_at=datetime.now(UTC),
        )
        checked.append(bet)

    uow.commit()
    return {"checked": len(checked), "skipped": skipped, "bets": checked}


def bets_summary(uow: UnitOfWork) -> dict[str, Any]:
    rows = uow.bets.summary()
    total_spent = sum((row["spent"] for row in rows), Decimal("0.00"))
    total_returned = sum((row["returned"] for row in rows), Decimal("0.00"))
    return {
        "rows": rows,
        "total_spent": money(total_spent),
        "total_returned": money(total_returned),
        "balance": money(total_returned - total_spent),
    }
