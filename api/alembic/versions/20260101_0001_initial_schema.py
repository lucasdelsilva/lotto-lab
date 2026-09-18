"""Esquema inicial do Lotto Lab

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "modality_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("modality", sa.String(32), nullable=False, unique=True),
        sa.Column("universe_min", sa.Integer(), nullable=False),
        sa.Column("universe_max", sa.Integer(), nullable=False),
        sa.Column("min_pick", sa.Integer(), nullable=False),
        sa.Column("max_pick", sa.Integer(), nullable=False),
        sa.Column("base_hits", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_valid_from", sa.Date(), nullable=False),
        sa.Column(
            "extra_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "import_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_contest", sa.Integer()),
        sa.Column("last_contest", sa.Integer()),
        sa.Column("first_drawn_at", sa.Date()),
        sa.Column("last_drawn_at", sa.Date()),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="COMPLETED"),
    )
    op.create_index("ix_import_batch_modality", "import_batch", ["modality"])

    op.create_table(
        "draw",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column("contest_no", sa.Integer(), nullable=False),
        sa.Column("drawn_at", sa.Date(), nullable=False),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "extras",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("prize_tiers", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "import_batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("import_batch.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint("modality", "contest_no", name="uq_draw_modality_contest"),
    )
    op.create_index("ix_draw_modality_contest", "draw", ["modality", "contest_no"])

    op.create_table(
        "analysis_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("draws_count", sa.Integer(), nullable=False),
        sa.Column("history_hash", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("modality", name="uq_snapshot_modality"),
    )

    op.create_table(
        "game_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("profile", sa.String(16), nullable=False),
        sa.Column("seed", sa.Integer()),
        sa.Column("numbers_per_game", sa.Integer(), nullable=False),
        sa.Column("games_count", sa.Integer(), nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_game_batch_modality", "game_batch", ["modality"])

    op.create_table(
        "game",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_batch.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "extras",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_score", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("already_drawn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "matched_contests",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'::integer[]"),
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_game_game_batch_id", "game", ["game_batch_id"])

    op.create_table(
        "bet",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("game.id", ondelete="SET NULL")
        ),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column("contest_no", sa.Integer(), nullable=False),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "extras",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("cost", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "placed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.CheckConstraint("cost >= 0", name="ck_bet_cost_non_negative"),
    )
    op.create_index("ix_bet_modality", "bet", ["modality"])
    op.create_index("ix_bet_game_id", "bet", ["game_id"])

    op.create_table(
        "bet_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bet.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("extra_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prize", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("bet_id", name="uq_bet_result_bet"),
    )


def downgrade() -> None:
    op.drop_table("bet_result")
    op.drop_index("ix_bet_game_id", table_name="bet")
    op.drop_index("ix_bet_modality", table_name="bet")
    op.drop_table("bet")
    op.drop_index("ix_game_game_batch_id", table_name="game")
    op.drop_table("game")
    op.drop_index("ix_game_batch_modality", table_name="game_batch")
    op.drop_table("game_batch")
    op.drop_table("analysis_snapshot")
    op.drop_index("ix_draw_modality_contest", table_name="draw")
    op.drop_table("draw")
    op.drop_index("ix_import_batch_modality", table_name="import_batch")
    op.drop_table("import_batch")
    op.drop_table("modality_config")
