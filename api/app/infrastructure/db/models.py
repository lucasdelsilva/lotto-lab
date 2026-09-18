"""Modelos SQLAlchemy 2.0, estilo declarativo tipado."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ModalityConfigModel(Base):
    __tablename__ = "modality_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    universe_min: Mapped[int] = mapped_column(Integer, nullable=False)
    universe_max: Mapped[int] = mapped_column(Integer, nullable=False)
    min_pick: Mapped[int] = mapped_column(Integer, nullable=False)
    max_pick: Mapped[int] = mapped_column(Integer, nullable=False)
    base_hits: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    extra_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ImportBatchModel(Base):
    __tablename__ = "import_batch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_contest: Mapped[int | None] = mapped_column(Integer)
    last_contest: Mapped[int | None] = mapped_column(Integer)
    first_drawn_at: Mapped[date | None] = mapped_column(Date)
    last_drawn_at: Mapped[date | None] = mapped_column(Date)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="COMPLETED")

    draws: Mapped[list[DrawModel]] = relationship(back_populates="import_batch")


class DrawModel(Base):
    __tablename__ = "draw"
    __table_args__ = (
        UniqueConstraint("modality", "contest_no", name="uq_draw_modality_contest"),
        Index("ix_draw_modality_contest", "modality", "contest_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    contest_no: Mapped[int] = mapped_column(Integer, nullable=False)
    drawn_at: Mapped[date] = mapped_column(Date, nullable=False)
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prize_tiers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batch.id", ondelete="SET NULL")
    )

    import_batch: Mapped[ImportBatchModel | None] = relationship(back_populates="draws")


class AnalysisSnapshotModel(Base):
    __tablename__ = "analysis_snapshot"
    __table_args__ = (UniqueConstraint("modality", name="uq_snapshot_modality"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    draws_count: Mapped[int] = mapped_column(Integer, nullable=False)
    history_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class GameBatchModel(Base):
    __tablename__ = "game_batch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    profile: Mapped[str] = mapped_column(String(16), nullable=False)
    seed: Mapped[int | None] = mapped_column(Integer)
    numbers_per_game: Mapped[int] = mapped_column(Integer, nullable=False)
    games_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    games: Mapped[list[GameModel]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="GameModel.position",
    )


class GameModel(Base):
    __tablename__ = "game"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    engine_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    already_drawn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matched_contests: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    batch: Mapped[GameBatchModel] = relationship(back_populates="games")
    bets: Mapped[list[BetModel]] = relationship(back_populates="game")


class BetModel(Base):
    __tablename__ = "bet"
    __table_args__ = (CheckConstraint("cost >= 0", name="ck_bet_cost_non_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("game.id", ondelete="SET NULL"), index=True
    )
    modality: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    contest_no: Mapped[int] = mapped_column(Integer, nullable=False)
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")

    game: Mapped[GameModel | None] = relationship(back_populates="bets")
    result: Mapped[BetResultModel | None] = relationship(
        back_populates="bet", cascade="all, delete-orphan", uselist=False
    )


class BetResultModel(Base):
    __tablename__ = "bet_result"
    __table_args__ = (UniqueConstraint("bet_id", name="uq_bet_result_bet"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bet.id", ondelete="CASCADE"), nullable=False
    )
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prize: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    bet: Mapped[BetModel] = relationship(back_populates="result")
