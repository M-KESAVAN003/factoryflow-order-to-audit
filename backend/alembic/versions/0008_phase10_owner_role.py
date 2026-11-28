"""Phase 10: Add dedicated 'owner' role to user_role_enum.

Revision ID: 0008_phase10_owner_role
Revises: 0007_phase8_offline_sync
Create Date: 2026-11-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_phase10_owner_role"
down_revision: Union[str, None] = "0007_phase8_offline_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'owner'")
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "role",
                existing_type=sa.Enum(
                    "admin",
                    "order_manager",
                    "floor_supervisor",
                    "qa_inspector",
                    "auditor",
                    name="user_role_enum",
                ),
                type_=sa.Enum(
                    "admin",
                    "order_manager",
                    "floor_supervisor",
                    "qa_inspector",
                    "auditor",
                    "owner",
                    name="user_role_enum",
                ),
                existing_nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "role",
                existing_type=sa.Enum(
                    "admin",
                    "order_manager",
                    "floor_supervisor",
                    "qa_inspector",
                    "auditor",
                    "owner",
                    name="user_role_enum",
                ),
                type_=sa.Enum(
                    "admin",
                    "order_manager",
                    "floor_supervisor",
                    "qa_inspector",
                    "auditor",
                    name="user_role_enum",
                ),
                existing_nullable=False,
            )
