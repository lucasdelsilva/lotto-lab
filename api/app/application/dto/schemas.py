"""Contratos de entrada e saida da API. Pydantic v2."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AlreadyDrawnPolicy, BetStatus, FilterId, Modality, Profile


class FiltersRequest(BaseModel):
    """Filtros ligados, por id. Omitir a lista liga todos os filtros da modalidade."""

    model_config = ConfigDict(extra="forbid")

    enabled: list[FilterId] | None = None
    max_consecutive: int | None = Field(default=None, ge=0)
    min_quadrants_covered: int = Field(default=0, ge=0, le=4)
    # Jogo cuja combinacao ja saiu e descartado e regerado, nunca aparece na resposta.
    on_already_drawn: AlreadyDrawnPolicy = AlreadyDrawnPolicy.REJECT


class GenerateExtras(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month_strategy: str = Field(default="auto", pattern="^(auto|fixed|random)$")
    month: int | None = Field(default=None, ge=1, le=12)
    column_picks: list[int] | None = None


class GenerateGamesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numbers_per_game: int = Field(ge=1)
    games: int = Field(default=1, ge=1, le=200)
    profile: Profile = Profile.BALANCED
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    budget_limit: Decimal | None = Field(default=None, ge=0)
    filters: FiltersRequest = Field(default_factory=FiltersRequest)
    weights: dict[str, float] | None = None
    extras: GenerateExtras = Field(default_factory=GenerateExtras)
    window: int = Field(default=50, ge=5, le=1000)
    max_overlap: int | None = Field(default=None, ge=0)


class GameSummary(BaseModel):
    """Resposta enxuta da geracao: dezenas e a marca de combinacao ja sorteada."""

    id: UUID
    numbers: list[int]
    already_drawn: bool
    extras: dict[str, Any] | None = None


class CostSummary(BaseModel):
    per_game: Decimal
    total: Decimal
    within_budget: bool


class GenerateGamesResponse(BaseModel):
    batch_id: UUID
    modality: Modality
    seed: int
    games: list[GameSummary]
    cost: CostSummary


class GameInsight(BaseModel):
    """Detalhamento sob demanda. Nunca volta na geracao."""

    id: UUID
    batch_id: UUID
    modality: Modality
    numbers: list[int]
    extras: dict[str, Any]
    engine_score: float
    already_drawn: bool
    matched_contests: list[int]
    metrics: dict[str, Any]
    pattern_ranges: dict[str, dict[str, float]]
    fit_score: float
    best_historical_match: dict[str, Any]
    drawn_subsets: list[dict[str, Any]]
    hot_numbers_used: list[int]
    cold_numbers_used: list[int]
    overdue_numbers_used: list[int]


class DrawResponse(BaseModel):
    contest_no: int
    drawn_at: date
    numbers: list[int]
    extras: dict[str, Any]


class PaginatedDraws(BaseModel):
    items: list[DrawResponse]
    total: int
    limit: int
    offset: int


class ImportBatchResponse(BaseModel):
    id: UUID
    modality: Modality
    filename: str
    file_hash: str
    rows_imported: int
    first_contest: int | None
    last_contest: int | None
    first_drawn_at: date | None
    last_drawn_at: date | None
    imported_at: datetime
    status: str


class CreateBetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_id: UUID | None = None
    modality: Modality | None = None
    contest_no: int = Field(ge=1)
    numbers: list[int] | None = None
    extras: dict[str, Any] = Field(default_factory=dict)
    cost: Decimal | None = Field(default=None, ge=0)


class BetResultResponse(BaseModel):
    hits: int
    extra_hit: bool
    prize: Decimal
    checked_at: datetime


class BetResponse(BaseModel):
    id: UUID
    game_id: UUID | None
    modality: Modality
    contest_no: int
    numbers: list[int]
    extras: dict[str, Any]
    cost: Decimal
    placed_at: datetime
    status: BetStatus
    result: BetResultResponse | None = None


class PaginatedBets(BaseModel):
    items: list[BetResponse]
    total: int
    limit: int
    offset: int


class CheckBetsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modality: Modality | None = None


class CheckBetsResponse(BaseModel):
    checked: int
    skipped: int
    results: list[BetResponse]


class SummaryRow(BaseModel):
    modality: Modality
    month: str
    bets: int
    spent: Decimal
    returned: Decimal
    balance: Decimal


class BetsSummary(BaseModel):
    rows: list[SummaryRow]
    total_spent: Decimal
    total_returned: Decimal
    balance: Decimal


class AIReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: UUID | None = None
    game_ids: list[UUID] | None = None
