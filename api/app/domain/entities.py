"""Entidades de dominio. Estruturas puras, sem dependencia de ORM nem de framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.enums import BetStatus, ImportStatus, Modality, Profile


@dataclass(frozen=True, slots=True)
class Draw:
    """Um concurso ja sorteado."""

    modality: Modality
    contest_no: int
    drawn_at: date
    numbers: tuple[int, ...]
    extras: dict[str, Any] = field(default_factory=dict)
    prize_tiers: dict[str, Any] | None = None
    id: UUID | None = None
    import_batch_id: UUID | None = None

    @property
    def month_of_luck(self) -> int | None:
        value = self.extras.get("month")
        return int(value) if value is not None else None

    @property
    def columns(self) -> tuple[int, ...] | None:
        value = self.extras.get("columns")
        return tuple(int(item) for item in value) if value is not None else None


@dataclass(frozen=True, slots=True)
class ImportBatch:
    modality: Modality
    filename: str
    file_hash: str
    rows_imported: int
    first_contest: int | None
    last_contest: int | None
    first_drawn_at: date | None
    last_drawn_at: date | None
    imported_at: datetime
    status: ImportStatus
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    modality: Modality
    computed_at: datetime
    draws_count: int
    history_hash: str
    payload: dict[str, Any]
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GameMetrics:
    """Metricas calculadas de um jogo. Nao volta na resposta da geracao, so no insight."""

    total_sum: int
    even_count: int
    odd_count: int
    prime_count: int
    spread: int
    max_consecutive: int
    consecutive_pairs: int
    quadrants: tuple[int, ...]
    endings: dict[int, int]
    multiples_of_3: int
    multiples_of_5: int
    mean: float
    median: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "sum": self.total_sum,
            "even": self.even_count,
            "odd": self.odd_count,
            "primes": self.prime_count,
            "spread": self.spread,
            "max_consecutive": self.max_consecutive,
            "consecutive_pairs": self.consecutive_pairs,
            "quadrants": list(self.quadrants),
            "endings": {str(k): v for k, v in self.endings.items()},
            "multiples_of_3": self.multiples_of_3,
            "multiples_of_5": self.multiples_of_5,
            "mean": self.mean,
            "median": self.median,
        }


@dataclass(frozen=True, slots=True)
class Game:
    numbers: tuple[int, ...]
    extras: dict[str, Any] = field(default_factory=dict)
    engine_score: float = 0.0
    fit_score: float = 0.0
    already_drawn: bool = False
    matched_contests: tuple[int, ...] = ()
    drawn_subsets: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = ()
    metrics: GameMetrics | None = None
    id: UUID | None = None
    game_batch_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GameBatch:
    modality: Modality
    created_at: datetime
    profile: Profile
    seed: int | None
    numbers_per_game: int
    games_count: int
    total_cost: Decimal
    params: dict[str, Any]
    games: tuple[Game, ...] = ()
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Bet:
    modality: Modality
    contest_no: int
    cost: Decimal
    placed_at: datetime
    status: BetStatus
    numbers: tuple[int, ...]
    extras: dict[str, Any] = field(default_factory=dict)
    game_id: UUID | None = None
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class BetResult:
    bet_id: UUID
    hits: int
    extra_hit: bool
    prize: Decimal
    checked_at: datetime
    id: UUID | None = None
