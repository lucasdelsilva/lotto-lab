"""Detalhamento de um jogo. Chamado apenas quando o usuario abre o jogo na tela."""

from __future__ import annotations

import uuid
from typing import Any

from app.analytics.delays import OVERDUE_RATIO, delay_report
from app.analytics.frequency import classify, z_scores
from app.analytics.history_index import HistoryIndex
from app.analytics.patterns import describe_game, fit_score, historical_metrics, percentile_ranges
from app.application.use_cases.run_analysis import REFERENCE_WINDOW, load_history
from app.core.errors import NotFoundError
from app.domain.enums import Modality, NumberTemperature
from app.infrastructure.db.uow import UnitOfWork


def explain_game(uow: UnitOfWork, game_id: uuid.UUID) -> dict[str, Any]:
    model = uow.games.get_game(game_id)
    if model is None:
        raise NotFoundError(f"Jogo {game_id} nao encontrado.")

    modality = Modality(model.batch.modality)
    history = load_history(uow, modality)
    rule = history.rule
    numbers = list(model.numbers)

    ranges = percentile_ranges(historical_metrics(history.draws, rule))

    if rule.is_column_based:
        return {
            "id": str(model.id),
            "batch_id": str(model.game_batch_id),
            "modality": modality.value,
            "numbers": numbers,
            "extras": dict(model.extras or {}),
            "engine_score": float(model.engine_score),
            "already_drawn": model.already_drawn,
            "matched_contests": list(model.matched_contests or []),
            "metrics": dict(model.metrics or {}),
            "pattern_ranges": {},
            "fit_score": 1.0,
            "best_historical_match": {"contest": None, "hits": 0},
            "drawn_subsets": [],
            "hot_numbers_used": [],
            "cold_numbers_used": [],
            "overdue_numbers_used": [],
        }

    metrics = describe_game(numbers, rule)
    index = HistoryIndex(history.draws, history.contests.tolist(), rule)
    evaluation = index.evaluate(numbers)

    z_values = z_scores(history.draws, rule, REFERENCE_WINDOW)
    delays = delay_report(history.draws, rule)

    hot: list[int] = []
    cold: list[int] = []
    overdue: list[int] = []
    for number in numbers:
        position = number - rule.universe_min
        temperature = classify(float(z_values[position]))
        if temperature is NumberTemperature.HOT:
            hot.append(number)
        elif temperature is NumberTemperature.COLD:
            cold.append(number)
        if float(delays.ratio[position]) >= OVERDUE_RATIO:
            overdue.append(number)

    return {
        "id": str(model.id),
        "batch_id": str(model.game_batch_id),
        "modality": modality.value,
        "numbers": numbers,
        "extras": dict(model.extras or {}),
        "engine_score": float(model.engine_score),
        "already_drawn": model.already_drawn,
        "matched_contests": list(model.matched_contests or []),
        "metrics": metrics.as_dict(),
        "pattern_ranges": ranges,
        "fit_score": fit_score(metrics, ranges),
        "best_historical_match": evaluation["best_historical_match"],
        "drawn_subsets": evaluation["drawn_subsets"],
        "hot_numbers_used": hot,
        "cold_numbers_used": cold,
        "overdue_numbers_used": overdue,
    }
