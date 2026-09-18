"""Geracao de jogos e persistencia do lote.

A resposta desse caso de uso e deliberadamente enxuta: dezenas, marca de combinacao ja
sorteada e custo. As metricas por jogo ficam gravadas no banco e so saem pelo endpoint de
insight, quando o usuario abre o jogo na tela.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.analytics.filters import FilterConfig
from app.analytics.generator import GenerationRequest, GenerationResult, generate
from app.application.dto.schemas import GenerateGamesRequest
from app.application.use_cases.run_analysis import load_history
from app.core.config import get_settings
from app.core.errors import BudgetExceededError, ValidationError
from app.core.logging import timed
from app.domain.entities import Game, GameBatch
from app.domain.enums import Modality
from app.domain.pricing import batch_cost, validate_pick_count
from app.infrastructure.db.uow import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerationOutput:
    batch_id: str
    modality: Modality
    seed: int
    games: list[dict[str, Any]]
    per_game_cost: Decimal
    total_cost: Decimal
    within_budget: bool


def _to_filter_config(modality: Modality, request: GenerateGamesRequest) -> FilterConfig:
    filters = request.filters
    base = FilterConfig.for_modality(
        modality, [item.value for item in filters.enabled] if filters.enabled is not None else None
    )
    return FilterConfig(
        enabled=base.enabled,
        on_already_drawn=filters.on_already_drawn,
        max_consecutive=filters.max_consecutive,
        min_quadrants_covered=filters.min_quadrants_covered,
    )


def _public_extras(extras: dict[str, Any]) -> dict[str, Any] | None:
    """Da geracao so voltam os extras que fazem parte da aposta, nunca as metricas."""
    for key in ("columns", "month"):
        if key in extras:
            return {key: extras[key]}
    return None


def generate_games(
    uow: UnitOfWork, modality: Modality, request: GenerateGamesRequest
) -> GenerationOutput:
    settings = get_settings()
    rule = validate_pick_count(modality, request.numbers_per_game)

    extras_for_cost: dict[str, Any] | None = None
    column_picks: tuple[int, ...] | None = None
    if rule.is_column_based and request.extras.column_picks:
        column_picks = tuple(request.extras.column_picks)
        extras_for_cost = {"column_picks": list(column_picks)}

    unit_cost, total_cost = batch_cost(
        modality, request.numbers_per_game, request.games, extras_for_cost
    )
    within_budget = True
    if request.budget_limit is not None:
        within_budget = total_cost <= request.budget_limit
        if not within_budget:
            raise BudgetExceededError(
                f"O lote custa R$ {total_cost} e o limite informado e R$ "
                f"{request.budget_limit}. Reduza a quantidade de jogos ou de numeros.",
                extra={
                    "total_cost": str(total_cost),
                    "budget_limit": str(request.budget_limit),
                    "per_game": str(unit_cost.total),
                },
            )

    history = load_history(uow, modality)
    if rule.modality is Modality.DIA_DE_SORTE and not history.months:
        raise ValidationError(
            "O historico do Dia de Sorte nao tem o mes da sorte. Reimporte a planilha."
        )

    filter_config = _to_filter_config(modality, request)

    generation_request = GenerationRequest(
        numbers_per_game=request.numbers_per_game,
        games=request.games,
        profile=request.profile,
        seed=request.seed,
        weights_override=request.weights,
        filters=filter_config,
        max_overlap=request.max_overlap,
        window=request.window,
        column_picks=column_picks,
        month_strategy=request.extras.month_strategy,
        month=request.extras.month,
        max_attempts=settings.generator_max_attempts,
        pool_factor=settings.generator_pool_factor,
    )

    with timed(
        logger,
        "generate_games",
        modality=modality.value,
        games=request.games,
        numbers=request.numbers_per_game,
    ) as context:
        result: GenerationResult = generate(
            history.draws, history.contests, rule, generation_request, months=history.months
        )
        context["attempts"] = result.attempts

    batch = GameBatch(
        modality=modality,
        created_at=datetime.now(UTC),
        profile=request.profile,
        seed=result.seed,
        numbers_per_game=request.numbers_per_game,
        games_count=len(result.games),
        total_cost=total_cost,
        params={
            # Guarda a configuracao resolvida, e nao o pedido cru, para que o lote possa
            # ser reproduzido mesmo quando o request veio sem a lista de filtros.
            "filters": filter_config.as_dict(),
            "weights": result.weights.as_dict(),
            "window": request.window,
            "max_overlap": request.max_overlap,
            "extras": request.extras.model_dump(mode="json"),
            "attempts": result.attempts,
            "rejections": result.rejections,
            "budget_limit": str(request.budget_limit) if request.budget_limit else None,
            "history_hash": history.history_hash,
        },
        games=tuple(
            Game(
                numbers=game.numbers,
                extras=game.extras
                | {
                    "fit_score": game.fit_score,
                    "number_score": game.number_score,
                    "best_historical_match": game.best_historical_match,
                    "drawn_subsets": game.drawn_subsets,
                },
                engine_score=game.engine_score,
                fit_score=game.fit_score,
                already_drawn=game.already_drawn,
                matched_contests=game.matched_contests,
                metrics=game.metrics,
            )
            for game in result.games
        ),
    )

    model = uow.games.add_batch(batch)
    uow.commit()

    return GenerationOutput(
        batch_id=str(model.id),
        modality=modality,
        seed=result.seed,
        games=[
            {
                "id": str(game_model.id),
                "numbers": list(game_model.numbers),
                "already_drawn": game_model.already_drawn,
                "extras": _public_extras(game_model.extras),
            }
            for game_model in model.games
        ],
        per_game_cost=unit_cost.total,
        total_cost=total_cost,
        within_budget=within_budget,
    )
