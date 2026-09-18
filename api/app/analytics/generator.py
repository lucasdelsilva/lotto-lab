"""Gerador de jogos. Pipeline deterministico, reprodutivel pela seed.

Sequencia de cada candidato:

1. amostragem sem reposicao ponderada pelo score, recalculando o componente de
   co-ocorrencia a cada dezena escolhida;
2. filtros rigidos, candidato reprovado e descartado;
3. diversificacao contra os jogos ja aceitos no mesmo lote;
4. verificacao contra o historico, preenchendo already_drawn e matched_contests.

No fim, um pool de varias vezes o pedido e ordenado por engine_score e os melhores sao
devolvidos.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.analytics import supersete
from app.analytics.filters import FilterConfig, build_bounds, evaluate
from app.analytics.frequency import IntArray
from app.analytics.history_index import HistoryIndex
from app.analytics.patterns import describe_game, fit_score, historical_metrics, percentile_ranges
from app.analytics.scoring import NumberScorer, ProfileWeights, normalize, weights_for
from app.core.errors import GenerationExhaustedError
from app.domain.entities import GameMetrics
from app.domain.enums import AlreadyDrawnPolicy, Modality, Profile
from app.domain.rules import ModalityRule

DEFAULT_MAX_ATTEMPTS = 20_000
DEFAULT_POOL_FACTOR = 5
NUMBER_SCORE_WEIGHT = 0.6
FIT_SCORE_WEIGHT = 0.4


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    numbers_per_game: int
    games: int
    profile: Profile = Profile.BALANCED
    seed: int | None = None
    weights_override: dict[str, float] | None = None
    filters: FilterConfig = field(default_factory=FilterConfig)
    max_overlap: int | None = None
    window: int = 50
    column_picks: tuple[int, ...] | None = None
    month_strategy: str = "auto"
    month: int | None = None
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    pool_factor: int = DEFAULT_POOL_FACTOR


@dataclass(frozen=True, slots=True)
class GeneratedGame:
    numbers: tuple[int, ...]
    extras: dict[str, Any]
    engine_score: float
    fit_score: float
    number_score: float
    already_drawn: bool
    matched_contests: tuple[int, ...]
    drawn_subsets: list[dict[str, Any]]
    best_historical_match: dict[str, Any]
    metrics: GameMetrics | None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    games: list[GeneratedGame]
    seed: int
    attempts: int
    rejections: dict[str, int]
    weights: ProfileWeights


def _resolve_seed(seed: int | None) -> int:
    if seed is not None:
        return int(seed)
    return int(np.random.SeedSequence().generate_state(1)[0] % (2**31 - 1))


def _sample_numbers(
    scorer: NumberScorer, rule: ModalityRule, size: int, rng: np.random.Generator
) -> list[int]:
    """Amostragem sem reposicao ponderada, com o peso de co-ocorrencia atualizado a cada
    dezena escolhida."""
    universe = np.arange(rule.universe_min, rule.universe_max + 1, dtype=np.int64)
    available = np.ones(rule.universe_size, dtype=bool)
    selected: list[int] = []

    for _ in range(size):
        scores = np.clip(scorer.scores(selected), 0.0, None)
        weights = scores[available] + 1e-9
        probabilities = weights / weights.sum()
        choice = rng.choice(universe[available], p=probabilities)
        selected.append(int(choice))
        available[int(choice) - rule.universe_min] = False

    return sorted(selected)


def _pick_month(
    draws_extras: list[int], rng: np.random.Generator, strategy: str, fixed: int | None
) -> int:
    """Mes da sorte escolhido pela mesma logica de frequencia e atraso das dezenas."""
    if strategy == "fixed" and fixed is not None:
        return int(fixed)
    if not draws_extras:
        return int(rng.integers(1, 13))

    months = np.asarray(draws_extras, dtype=np.int64)
    counts = np.bincount(months, minlength=13)[1:].astype(np.float64)
    if strategy == "random":
        return int(rng.integers(1, 13))

    delays = np.zeros(12, dtype=np.float64)
    total = months.shape[0]
    for month in range(1, 13):
        appearances = np.flatnonzero(months == month)
        delays[month - 1] = total - 1 - int(appearances[-1]) if appearances.size else total
    averages = np.where(counts > 0, total / np.maximum(counts, 1.0), float(total))
    ratio = delays / np.maximum(averages, 1e-9)

    score = 0.5 * normalize(counts) + 0.5 * normalize(ratio) + 1e-9
    probabilities = score / score.sum()
    return int(rng.choice(np.arange(1, 13), p=probabilities))


def generate(
    draws: IntArray,
    contests: IntArray,
    rule: ModalityRule,
    request: GenerationRequest,
    months: list[int] | None = None,
) -> GenerationResult:
    if rule.is_column_based:
        return _generate_columns(draws, contests, rule, request)

    seed = _resolve_seed(request.seed)
    rng = np.random.default_rng(seed)
    weights = weights_for(request.profile, request.weights_override)
    scorer = NumberScorer(draws, rule, weights, window=request.window)
    index = HistoryIndex(draws, contests.tolist(), rule)
    # O peso normalizado por dezena alimenta tanto o filtro de Pesos quanto a faixa
    # historica dele, entao os dois olham exatamente a mesma escala.
    number_scores = normalize(np.clip(scorer.static_scores(), 0.0, None))
    bounds = build_bounds(draws, rule, number_scores)
    ranges = percentile_ranges(historical_metrics(draws, rule))

    max_overlap = (
        request.max_overlap
        if request.max_overlap is not None
        else max(1, rule.base_hits - 2)
    )
    target_pool = max(request.games, request.games * request.pool_factor)

    pool: list[GeneratedGame] = []
    accepted_sets: list[set[int]] = []
    rejections: Counter[str] = Counter()
    attempts = 0

    while len(pool) < target_pool and attempts < request.max_attempts:
        attempts += 1
        numbers = _sample_numbers(scorer, rule, request.numbers_per_game, rng)

        outcome = evaluate(numbers, rule, request.filters, bounds, number_scores)
        if not outcome.accepted:
            rejections[outcome.reasons[0]] += 1
            continue

        candidate = set(numbers)
        if any(len(candidate & existing) > max_overlap for existing in accepted_sets):
            rejections[f"sobreposicao maior que {max_overlap} com outro jogo do lote"] += 1
            continue

        history = index.evaluate(numbers)
        if (
            history["already_drawn"]
            and request.filters.on_already_drawn is AlreadyDrawnPolicy.REJECT
        ):
            rejections["combinacao ja sorteada"] += 1
            continue

        metrics = describe_game(numbers, rule)
        fit = fit_score(metrics, ranges)
        number_score = scorer.score_of(numbers)
        extras: dict[str, Any] = {}
        if rule.modality is Modality.DIA_DE_SORTE:
            extras["month"] = _pick_month(
                months or [], rng, request.month_strategy, request.month
            )

        pool.append(
            GeneratedGame(
                numbers=tuple(numbers),
                extras=extras,
                engine_score=round(
                    NUMBER_SCORE_WEIGHT * number_score + FIT_SCORE_WEIGHT * fit, 4
                ),
                fit_score=fit,
                number_score=number_score,
                already_drawn=bool(history["already_drawn"]),
                matched_contests=tuple(history["matched_contests"]),
                drawn_subsets=history["drawn_subsets"],
                best_historical_match=history["best_historical_match"],
                metrics=metrics,
            )
        )
        accepted_sets.append(candidate)

    if len(pool) < request.games:
        top_reasons = ", ".join(
            f"{reason} ({count}x)" for reason, count in rejections.most_common(3)
        )
        raise GenerationExhaustedError(
            f"Apos {attempts} tentativas foram gerados apenas {len(pool)} de "
            f"{request.games} jogos. Afrouxe os filtros ou aumente o limite. "
            f"Principais motivos de rejeicao: {top_reasons or 'nenhum'}."
        )

    pool.sort(key=lambda game: game.engine_score, reverse=True)
    return GenerationResult(
        games=pool[: request.games],
        seed=seed,
        attempts=attempts,
        rejections=dict(rejections),
        weights=weights,
    )


def _generate_columns(
    draws: IntArray, contests: IntArray, rule: ModalityRule, request: GenerationRequest
) -> GenerationResult:
    """Super Sete: amostra por coluna, respeitando 1 a 3 digitos por coluna."""
    from app.domain.pricing import distribute_columns

    seed = _resolve_seed(request.seed)
    rng = np.random.default_rng(seed)
    weights = weights_for(request.profile, request.weights_override)
    picks = request.column_picks or distribute_columns(request.numbers_per_game, rule)

    report = supersete.column_report(draws, rule, window=request.window)
    frequency = normalize(report.frequency.astype(np.float64).ravel()).reshape(
        rule.columns, supersete.DIGITS
    )
    delay = normalize(report.delay_ratio.ravel()).reshape(rule.columns, supersete.DIGITS)

    if weights.is_uniform:
        column_scores = np.ones((rule.columns, supersete.DIGITS), dtype=np.float64)
    else:
        total_weight = weights.freq + weights.global_freq + weights.delay
        total_weight = total_weight if total_weight > 0 else 1.0
        column_scores = (
            (weights.freq + weights.global_freq) * frequency + weights.delay * delay
        ) / total_weight

    seen: dict[tuple[tuple[int, ...], ...], None] = {}
    games: list[GeneratedGame] = []
    rejections: Counter[str] = Counter()
    attempts = 0

    while len(games) < request.games and attempts < request.max_attempts:
        attempts += 1
        columns: list[tuple[int, ...]] = []
        for column in range(rule.columns):
            scores = np.clip(column_scores[column], 0.0, None) + 1e-9
            probabilities = scores / scores.sum()
            digits = rng.choice(
                np.arange(supersete.DIGITS), size=picks[column], replace=False, p=probabilities
            )
            columns.append(tuple(sorted(int(digit) for digit in digits)))

        key = tuple(columns)
        if key in seen:
            rejections["combinacao de colunas repetida no lote"] += 1
            continue
        seen[key] = None

        flat = tuple(digit for column in columns for digit in column)
        already, matched = _supersete_history_match(columns, draws, contests)
        if already and request.filters.on_already_drawn is AlreadyDrawnPolicy.REJECT:
            rejections["combinacao ja sorteada"] += 1
            continue

        games.append(
            GeneratedGame(
                numbers=flat,
                extras={"columns": [list(column) for column in columns], "picks": list(picks)},
                engine_score=round(
                    float(
                        np.mean(
                            [
                                column_scores[index][list(column)].mean()
                                for index, column in enumerate(columns)
                            ]
                        )
                    ),
                    4,
                ),
                fit_score=1.0,
                number_score=0.0,
                already_drawn=already,
                matched_contests=tuple(matched),
                drawn_subsets=[],
                best_historical_match={"contest": None, "hits": 0},
                metrics=None,
            )
        )

    if len(games) < request.games:
        raise GenerationExhaustedError(
            f"Apos {attempts} tentativas foram gerados apenas {len(games)} de "
            f"{request.games} jogos do Super Sete."
        )

    games.sort(key=lambda game: game.engine_score, reverse=True)
    return GenerationResult(
        games=games, seed=seed, attempts=attempts, rejections=dict(rejections), weights=weights
    )


def _supersete_history_match(
    columns: list[tuple[int, ...]], draws: IntArray, contests: IntArray
) -> tuple[bool, list[int]]:
    """Um volante do Super Sete cobre um concurso quando cada coluna contem o digito sorteado."""
    if draws.shape[0] == 0:
        return False, []
    matched: list[int] = []
    for row, contest in zip(draws, contests, strict=True):
        if all(int(row[index]) in columns[index] for index in range(len(columns))):
            matched.append(int(contest))
    return bool(matched), matched
