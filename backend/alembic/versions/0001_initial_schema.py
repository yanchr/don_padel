"""Initial schema for venues and availability snapshots.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("venues_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshots_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"], unique=False)
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"], unique=False)

    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("playtomic_venue_id", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playtomic_venue_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_venues_country", "venues", ["country"], unique=False)
    op.create_index("ix_venues_name", "venues", ["name"], unique=False)
    op.create_index("ix_venues_playtomic_venue_id", "venues", ["playtomic_venue_id"], unique=False)

    op.create_table(
        "availability_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venue_id", sa.Integer(), nullable=False),
        sa.Column("court_label", sa.String(length=255), nullable=False),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("available_spots", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_availability_snapshots_captured_at", "availability_snapshots", ["captured_at"], unique=False)
    op.create_index("ix_availability_snapshots_slot_end", "availability_snapshots", ["slot_end"], unique=False)
    op.create_index("ix_availability_snapshots_slot_start", "availability_snapshots", ["slot_start"], unique=False)
    op.create_index("ix_availability_snapshots_status", "availability_snapshots", ["status"], unique=False)
    op.create_index("ix_availability_snapshots_venue_id", "availability_snapshots", ["venue_id"], unique=False)
    op.create_index(
        "ix_availability_snapshots_venue_slot_start",
        "availability_snapshots",
        ["venue_id", "slot_start"],
        unique=False,
    )
    op.create_index(
        "ix_availability_snapshots_captured_desc",
        "availability_snapshots",
        [sa.text("captured_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_availability_snapshots_captured_desc", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_venue_slot_start", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_venue_id", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_status", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_slot_start", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_slot_end", table_name="availability_snapshots")
    op.drop_index("ix_availability_snapshots_captured_at", table_name="availability_snapshots")
    op.drop_table("availability_snapshots")

    op.drop_index("ix_venues_playtomic_venue_id", table_name="venues")
    op.drop_index("ix_venues_name", table_name="venues")
    op.drop_index("ix_venues_country", table_name="venues")
    op.drop_table("venues")

    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_started_at", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
