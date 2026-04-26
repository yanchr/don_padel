"""Add per-court daily Playtomic availability snapshots.

Revision ID: 0002_playtomic_day_snap
Revises: 0001_initial_schema
Create Date: 2026-04-26 10:47:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_playtomic_day_snap"
down_revision: str | None = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "playtomic_court_day_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venue_id", sa.Integer(), nullable=False),
        sa.Column("playtomic_resource_id", sa.String(length=128), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("court_name", sa.String(length=255), nullable=True),
        sa.Column("slots_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "venue_id",
            "playtomic_resource_id",
            "day",
            name="uq_playtomic_court_day_snapshots_venue_resource_day",
        ),
    )
    op.create_index(
        "ix_playtomic_court_day_snapshots_venue_id",
        "playtomic_court_day_snapshots",
        ["venue_id"],
        unique=False,
    )
    op.create_index(
        "ix_playtomic_court_day_snapshots_playtomic_resource_id",
        "playtomic_court_day_snapshots",
        ["playtomic_resource_id"],
        unique=False,
    )
    op.create_index(
        "ix_playtomic_court_day_snapshots_day",
        "playtomic_court_day_snapshots",
        ["day"],
        unique=False,
    )
    op.create_index(
        "ix_playtomic_court_day_snapshots_captured_at",
        "playtomic_court_day_snapshots",
        ["captured_at"],
        unique=False,
    )
    op.create_index(
        "ix_playtomic_court_day_snapshots_venue_day",
        "playtomic_court_day_snapshots",
        ["venue_id", "day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_playtomic_court_day_snapshots_venue_day",
        table_name="playtomic_court_day_snapshots",
    )
    op.drop_index(
        "ix_playtomic_court_day_snapshots_captured_at",
        table_name="playtomic_court_day_snapshots",
    )
    op.drop_index(
        "ix_playtomic_court_day_snapshots_day",
        table_name="playtomic_court_day_snapshots",
    )
    op.drop_index(
        "ix_playtomic_court_day_snapshots_playtomic_resource_id",
        table_name="playtomic_court_day_snapshots",
    )
    op.drop_index(
        "ix_playtomic_court_day_snapshots_venue_id",
        table_name="playtomic_court_day_snapshots",
    )
    op.drop_table("playtomic_court_day_snapshots")
