"""Baseline migration: create all 10 tables and seed scoring_methods v1.

Revision ID: 0001
Revises:
Create Date: 2026-06-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- scoring_methods (referenced by tool_profiles, rankings) ---
    op.create_table(
        "scoring_methods",
        sa.Column("version", sa.String(), primary_key=True),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        INSERT INTO scoring_methods (version, weights, description) VALUES (
            'v1',
            '{"popularity": 0.30, "momentum": 0.30, "technical_merit": 0.25, "source_credibility": 0.15}'::jsonb,
            'Initial weighted composite: popularity 30%, momentum 30%, technical_merit 25%, source_credibility 15%'
        )
        """
    )

    # --- agent_configs ---
    op.create_table(
        "agent_configs",
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # --- discovery_sources ---
    op.create_table(
        "discovery_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(), nullable=False, unique=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # --- tools ---
    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("homepage_url", sa.String(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tools_canonical_name", "tools", ["canonical_name"])

    # --- reports (no FK to runs yet — runs will FK to reports, causing circular dep) ---
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("markdown_path", sa.String(), nullable=False),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("pdf_status", sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("review_notes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reports_generated_at", "reports", ["generated_at"])

    # --- runs ---
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=True),
        sa.Column("config_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_created_at", "runs", ["created_at"])

    # Add FK from reports.run_id → runs.id (deferred to avoid circular)
    op.create_foreign_key("fk_reports_run_id", "reports", "runs", ["run_id"], ["id"])

    # --- run_steps ---
    op.create_table(
        "run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_run_steps_run_id_step", "run_steps", ["run_id", "step"])

    # --- candidates ---
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discovery_sources.id"), nullable=False),
        sa.Column("raw_name", sa.String(), nullable=False),
        sa.Column("normalized_name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("canonical_domain", sa.String(), nullable=True),
        sa.Column("raw_signals", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tools.id"), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("exclusion_reason", sa.String(), nullable=True),
    )
    op.create_index("ix_candidates_run_id", "candidates", ["run_id"])
    op.create_index("ix_candidates_normalized_name", "candidates", ["normalized_name"])
    op.create_index("ix_candidates_tool_id", "candidates", ["tool_id"])

    # --- tool_profiles ---
    op.create_table(
        "tool_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("research_summary", sa.Text(), nullable=False),
        sa.Column("trend_rationale", sa.Text(), nullable=False),
        sa.Column("technical_strengths", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("technical_weaknesses", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("comparison", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_components", postgresql.JSONB(), nullable=False),
        sa.Column("scoring_method_version", sa.String(), sa.ForeignKey("scoring_methods.version"), nullable=False),
        sa.Column("analysis_gaps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_tool_profiles_report_tool", "tool_profiles", ["report_id", "tool_id"])
    op.create_index("ix_tool_profiles_tool_id", "tool_profiles", ["tool_id"])
    op.create_index("ix_tool_profiles_report_id", "tool_profiles", ["report_id"])

    # --- rankings ---
    op.create_table(
        "rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id"), unique=True, nullable=False),
        sa.Column("scoring_method_version", sa.String(), sa.ForeignKey("scoring_methods.version"), nullable=False),
        sa.Column("ordered_entries", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("rankings")
    op.drop_table("tool_profiles")
    op.drop_table("candidates")
    op.drop_table("run_steps")
    op.drop_constraint("fk_reports_run_id", "reports", type_="foreignkey")
    op.drop_table("runs")
    op.drop_table("reports")
    op.drop_table("tools")
    op.drop_table("discovery_sources")
    op.drop_table("agent_configs")
    op.drop_table("scoring_methods")
