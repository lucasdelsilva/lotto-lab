"""Preview de custo em tempo real, consumido pela tela do gerador."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.domain.enums import Modality
from app.domain.pricing import preview_cost
from app.domain.rules import rule_for

router = APIRouter(prefix="/modalities/{modality}", tags=["pricing"])


@router.get("/pricing/preview")
def pricing_preview(
    modality: Modality,
    n: Annotated[int, Query(ge=0, description="Quantidade de numeros do volante")],
    games: Annotated[int, Query(ge=1, le=1000)] = 1,
    column_picks: Annotated[str | None, Query(description="Ex.: 2,2,1,1,1,1,1")] = None,
) -> dict[str, Any]:
    extras: dict[str, Any] | None = None
    if column_picks:
        extras = {"column_picks": [int(item) for item in column_picks.split(",")]}

    cost = preview_cost(modality, n, extras)
    return {
        "modality": modality.value,
        "numbers": cost.numbers,
        "combinations": cost.combinations,
        "base_price": str(cost.base_price),
        "per_game": str(cost.total),
        "total": str(cost.scaled(games)),
        "games": games,
        "column_picks": list(cost.column_picks) if cost.column_picks else None,
    }


@router.get("/rules")
def modality_rules(modality: Modality) -> dict[str, Any]:
    rule = rule_for(modality)
    return {
        "modality": modality.value,
        "label": modality.label,
        "universe_min": rule.universe_min,
        "universe_max": rule.universe_max,
        "min_pick": rule.min_pick,
        "max_pick": rule.max_pick,
        "base_hits": rule.base_hits,
        "base_price": str(rule.base_price),
        "is_column_based": rule.is_column_based,
        "columns": rule.columns,
        "column_min_pick": rule.column_min_pick,
        "column_max_pick": rule.column_max_pick,
        "board": {"rows": rule.board.rows, "cols": rule.board.cols} if rule.board else None,
        "extra_schema": rule.extra_schema,
    }


@router.get("/pricing/table")
def pricing_table(modality: Modality) -> dict[str, Any]:
    """Tabela completa de precos por quantidade de numeros, como a tabela oficial."""
    rule = rule_for(modality)
    rows = []
    for n in range(rule.min_pick, rule.max_pick + 1):
        cost = preview_cost(modality, n)
        rows.append(
            {
                "numbers": n,
                "combinations": cost.combinations,
                "price": str(cost.total),
                "column_picks": list(cost.column_picks) if cost.column_picks else None,
            }
        )
    return {"modality": modality.value, "rows": rows}
