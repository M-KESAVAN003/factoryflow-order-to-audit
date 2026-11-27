"""Phase 2: master data tables (units, unit_conversions, stock_items, products, suppliers, customers).

Revision ID: 0002_phase2
Revises: 0001_phase1
Create Date: 2026-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_phase2"
down_revision: Union[str, None] = "0001_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "units",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column(
            "dimension",
            sa.Enum("mass", "volume", "count", name="unit_dimension_enum"),
            nullable=False,
        ),
        sa.Column("is_base", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_units_symbol"), "units", ["symbol"], unique=True)

    op.create_table(
        "stock_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column(
            "item_type",
            sa.Enum("RAW_MATERIAL", "PACKAGING", "FINISHED_GOOD", name="stock_item_type_enum"),
            nullable=False,
        ),
        sa.Column("base_unit_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_unit_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_rate", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("reorder_level", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["base_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_items_item_type"), "stock_items", ["item_type"], unique=False)
    op.create_index(op.f("ix_stock_items_name"), "stock_items", ["name"], unique=False)
    op.create_index(op.f("ix_stock_items_sku"), "stock_items", ["sku"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pack_size", sa.String(length=60), nullable=False),
        sa.Column("selling_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("hsn_code", sa.String(length=20), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("pouch_stock_item_id", sa.String(length=36), nullable=True),
        sa.Column("carton_stock_item_id", sa.String(length=36), nullable=True),
        sa.Column("packets_per_carton", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["carton_stock_item_id"], ["stock_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pouch_stock_item_id"], ["stock_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_item_id"),
    )
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)

    op.create_table(
        "unit_conversions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("from_unit_id", sa.String(length=36), nullable=False),
        sa.Column("to_unit_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_unit_id",
            "to_unit_id",
            "product_id",
            name="uq_unit_conversion_pair_product",
        ),
    )
    op.create_index(op.f("ix_unit_conversions_from_unit_id"), "unit_conversions", ["from_unit_id"], unique=False)
    op.create_index(op.f("ix_unit_conversions_product_id"), "unit_conversions", ["product_id"], unique=False)
    op.create_index(op.f("ix_unit_conversions_to_unit_id"), "unit_conversions", ["to_unit_id"], unique=False)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("gstin", sa.String(length=15), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("state_code", sa.String(length=5), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_gstin"), "suppliers", ["gstin"], unique=True)
    op.create_index(op.f("ix_suppliers_name"), "suppliers", ["name"], unique=False)

    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "customer_type",
            sa.Enum("Retailer", "Distributor", name="customer_type_enum"),
            nullable=False,
        ),
        sa.Column("gstin", sa.String(length=15), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("state_code", sa.String(length=5), nullable=False),
        sa.Column("assigned_salesman_id", sa.String(length=36), nullable=True),
        sa.Column("credit_limit", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_salesman_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_assigned_salesman_id"), "customers", ["assigned_salesman_id"], unique=False)
    op.create_index(op.f("ix_customers_gstin"), "customers", ["gstin"], unique=True)
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_gstin"), table_name="customers")
    op.drop_index(op.f("ix_customers_assigned_salesman_id"), table_name="customers")
    op.drop_table("customers")

    op.drop_index(op.f("ix_suppliers_name"), table_name="suppliers")
    op.drop_index(op.f("ix_suppliers_gstin"), table_name="suppliers")
    op.drop_table("suppliers")

    op.drop_index(op.f("ix_unit_conversions_to_unit_id"), table_name="unit_conversions")
    op.drop_index(op.f("ix_unit_conversions_product_id"), table_name="unit_conversions")
    op.drop_index(op.f("ix_unit_conversions_from_unit_id"), table_name="unit_conversions")
    op.drop_table("unit_conversions")

    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_stock_items_sku"), table_name="stock_items")
    op.drop_index(op.f("ix_stock_items_name"), table_name="stock_items")
    op.drop_index(op.f("ix_stock_items_item_type"), table_name="stock_items")
    op.drop_table("stock_items")

    op.drop_index(op.f("ix_units_symbol"), table_name="units")
    op.drop_table("units")

    sa.Enum(name="customer_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="stock_item_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="unit_dimension_enum").drop(op.get_bind(), checkfirst=True)
