"""Curadoria do lote pela IA.

Monta o payload com estatisticas ja calculadas, chama o analista e valida a resposta:
se o ranking citar um id que nao estava em candidate_games, a resposta inteira e
descartada, porque um id inventado indica que o modelo saiu do conjunto informado.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.analytics.patterns import describe_game, quadrant_counts
from app.application.use_cases.run_analysis import REFERENCE_WINDOW, load_history, number_stats
from app.core.errors import NotFoundError
from app.infrastructure.ai.client import AIResult, get_analyst
from app.infrastructure.db.uow import UnitOfWork

logger = logging.getLogger(__name__)

TOP_NUMBERS_IN_PAYLOAD = 60
TOP_PAIRS_IN_PAYLOAD = 30


def build_ai_payload(uow: UnitOfWork, batch_id: uuid.UUID) -> dict[str, Any]:
    batch = uow.games.get_batch(batch_id)
    if batch is None:
        raise NotFoundError(f"Lote {batch_id} nao encontrado.")

    modality = batch.modality
    history = load_history(uow, modality)
    rule = history.rule

    stats = number_stats(history, REFERENCE_WINDOW)[:TOP_NUMBERS_IN_PAYLOAD]

    from app.analytics.cooccurrence import cooccurrence_report
    from app.analytics.patterns import historical_metrics, percentile_ranges
    from app.analytics.sequences import repeat_series

    ranges = percentile_ranges(historical_metrics(history.draws, rule))
    repeats = repeat_series(history.draws)
    pairs = cooccurrence_report(history.draws, rule).top_pairs(TOP_PAIRS_IN_PAYLOAD)

    candidates = []
    for game in batch.games:
        entry: dict[str, Any] = {
            "id": str(game.id),
            "numbers": list(game.numbers),
            "already_drawn": game.already_drawn,
            "drawn_subsets": game.extras.get("drawn_subsets", []),
            "best_historical_match": game.extras.get(
                "best_historical_match", {"contest": None, "hits": 0}
            ),
            "engine_score": game.engine_score,
        }
        if not rule.is_column_based:
            metrics = describe_game(list(game.numbers), rule)
            entry |= {
                "sum": metrics.total_sum,
                "even": metrics.even_count,
                "primes": metrics.prime_count,
                "consecutives": metrics.max_consecutive,
                "quadrants": list(quadrant_counts(list(game.numbers), rule)),
            }
        else:
            entry["columns"] = game.extras.get("columns", [])
        candidates.append(entry)

    return {
        "modality": modality.value,
        "rules": {
            "universe": rule.universe_size,
            "min": rule.min_pick,
            "max": rule.max_pick,
            "base_hits": rule.base_hits,
            "base_price": float(rule.base_price),
            "extra": list(rule.extra_schema) or None,
        },
        "request": {
            "numbers_per_game": batch.numbers_per_game,
            "games": batch.games_count,
            "profile": batch.profile.value,
            "budget_limit": batch.params.get("budget_limit"),
        },
        "history_meta": {
            "total_draws": history.total,
            "first_contest": int(history.contests[0]),
            "last_contest": int(history.contests[-1]),
            "imported_at": history.last_drawn_at,
        },
        "number_stats": stats,
        "pattern_ranges": {
            "sum": ranges.get("sum", {}),
            "even_count": ranges.get("even", {}),
            "primes": ranges.get("primes", {}),
            "consecutives": ranges.get("max_consecutive", {}),
            "range_spread": ranges.get("spread", {}),
            "repeat_from_previous": {
                "p10": int(repeats.min()) if repeats.size else 0,
                "p50": int(repeats.mean()) if repeats.size else 0,
                "p90": int(repeats.max()) if repeats.size else 0,
            },
        },
        "top_pairs": pairs,
        "candidate_games": candidates,
        "cost": {"total": float(batch.total_cost)},
    }


def review_batch(uow: UnitOfWork, batch_id: uuid.UUID) -> dict[str, Any]:
    payload = build_ai_payload(uow, batch_id)
    result: AIResult = get_analyst().review(payload)

    if result.available and result.analysis is not None:
        known_ids = {game["id"] for game in payload["candidate_games"]}
        cited = {ranked.id for ranked in result.analysis.ranked_games}
        unknown = cited - known_ids
        if unknown:
            logger.warning("ai.response.unknown_ids", extra={"unknown": sorted(unknown)})
            result = AIResult(
                available=False,
                error=(
                    "A resposta da IA citou jogos que nao estavam no lote "
                    f"({sorted(unknown)}). A resposta foi descartada."
                ),
                model=result.model,
                tokens=result.tokens,
            )

    return {"batch_id": str(batch_id), **result.as_dict()}
