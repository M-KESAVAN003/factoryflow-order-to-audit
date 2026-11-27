"""Phase 4: BOM headers/lines and production runs, materials, outputs, and wastage.

Revision ID: 0004_phase4
Revises: 0003_phase3
Create Date: 2026-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase4"
down_revision: Union[str, None] = "0003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stock_item_type_enum(bind) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(
            "RAW_MATERIAL",
            "PACKAGING",
            "FINISHED_GOOD",
            name="stock_item_type_enum",
            create_type=False,
        )
    return sa.Enum(
        "RAW_MATERIAL",
        "PACKAGING",
        "FINISHED_GOOD",
        name="stock_item_type_enum",
    )


def upgrade() -> None:
    bind = op.get_bind()
    item_type_enum = _stock_item_type_enum(bind)

    op.create_table(
        "bom_headers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("batch_size", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("expected_output", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("output_unit_id", sa.String(length=36), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "INACTIVE", name="bom_status_enum"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["output_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "version_number", name="uq_bom_product_version"),
    )
    op.create_index(op.f("ix_bom_headers_is_active"), "bom_headers", ["is_active"], unique=False)
    op.create_index(op.f("ix_bom_headers_product_id"), "bom_headers", ["product_id"], unique=False)
    op.create_index(op.f("ix_bom_headers_status"), "bom_headers", ["status"], unique=False)

    op.create_table(
        "bom_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("bom_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("input_category", item_type_enum, nullable=False),
        sa.Column("standard_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("base_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.ForeignKeyConstraint(["bom_id"], ["bom_headers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bom_lines_bom_id"), "bom_lines", ["bom_id"], unique=False)
    op.create_index(op.f("ix_bom_lines_stock_item_id"), "bom_lines", ["stock_item_id"], unique=False)

    op.create_table(
        "production_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("bom_id", sa.String(length=36), nullable=False),
        sa.Column("bom_version_snapshot", sa.Integer(), nullable=False),
        sa.Column("batch_number", sa.String(length=64), nullable=False),
        sa.Column("production_date", sa.Date(), nullable=False),
        sa.Column("planned_batches", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("expected_output", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("actual_good_output", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("damaged_packets", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("damaged_pouches", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("scrap_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("yield_variance_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("variance_tolerance_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("supervisor_id", sa.String(length=36), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PLANNED",
                "IN_PROGRESS",
                "COMPLETED",
                "POSTED",
                "CANCELLED",
                name="production_status_enum",
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", sa.String(length=36), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=36), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bom_id"], ["bom_headers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["posted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_runs_batch_number"), "production_runs", ["batch_number"], unique=False)
    op.create_index(op.f("ix_production_runs_bom_id"), "production_runs", ["bom_id"], unique=False)
    op.create_index(op.f("ix_production_runs_order_number"), "production_runs", ["order_number"], unique=True)
    op.create_index(op.f("ix_production_runs_product_id"), "production_runs", ["product_id"], unique=False)
    op.create_index(op.f("ix_production_runs_production_date"), "production_runs", ["production_date"], unique=False)
    op.create_index(op.f("ix_production_runs_status"), "production_runs", ["status"], unique=False)

    op.create_table(
        "production_materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("input_category", item_type_enum, nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("planned_base_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("actual_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("damaged_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_consumed_base_qty", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("variance_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("variance_status", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_materials_production_run_id"), "production_materials", ["production_run_id"], unique=False)
    op.create_index(op.f("ix_production_materials_stock_item_id"), "production_materials", ["stock_item_id"], unique=False)

    op.create_table(
        "production_outputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("good_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("damaged_packets", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("cartons_used", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("carton_capacity_packets", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unpacked_packets", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("packaging_warning", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_outputs_production_run_id"), "production_outputs", ["production_run_id"], unique=False)

    op.create_table(
        "production_wastage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=True),
        sa.Column("wastage_type", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.String(length=250), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_wastage_production_run_id"), "production_wastage", ["production_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_production_wastage_production_run_id"), table_name="production_wastage")
    op.drop_table("production_wastage")

    op.drop_index(op.f("ix_production_outputs_production_run_id"), table_name="production_outputs")
    op.drop_table("production_outputs")

    op.drop_index(op.f("ix_production_materials_stock_item_id"), table_name="production_materials")
    op.drop_index(op.f("ix_production_materials_production_run_id"), table_name="production_materials")
    op.drop_table("production_materials")

    op.drop_index(op.f("ix_production_runs_status"), table_name="production_runs")
    op.drop_index(op.f("ix_production_runs_production_date"), table_name="production_runs")
    op.drop_index(op.f("ix_production_runs_product_id"), table_name="production_runs")
    op.drop_index(op.f("ix_production_runs_order_number"), table_name="production_runs")
    op.drop_index(op.f("ix_production_runs_bom_id"), table_name="production_runs")
    op.drop_index(op.f("ix_production_runs_batch_number"), table_name="production_runs")
    op.drop_table("production_runs")

    op.drop_index(op.f("ix_bom_lines_stock_item_id"), table_name="bom_lines")
    op.drop_index(op.f("ix_bom_lines_bom_id"), table_name="bom_lines")
    op.drop_table("bom_lines")

    op.drop_index(op.f("ix_bom_headers_status"), table_name="bom_headers")
    op.drop_index(op.f("ix_bom_headers_product_id"), table_name="bom_headers")
    op.drop_index(op.f("ix_bom_headers_is_active"), table_name="bom_headers")
    op.drop_table("bom_headers")

    sa.Enum(name="production_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="bom_status_enum").drop(op.get_bind(), checkfirst=True)
