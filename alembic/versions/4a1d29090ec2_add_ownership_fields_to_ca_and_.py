"""Add ownership fields to CA and Certificate

Revision ID: 4a1d29090ec2
Revises: 9d90136388ec
Create Date: 2026-02-01 19:04:24.725386

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a1d29090ec2"
down_revision: Union[str, Sequence[str], None] = "9d90136388ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("certificate_authorities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("created_by_user_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_ca_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_ca_created_by_user_id",
            "users",
            ["created_by_user_id"],
            ["id"],
        )

    with op.batch_alter_table("certificates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("created_by_user_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_cert_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_cert_created_by_user_id",
            "users",
            ["created_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("certificates", schema=None) as batch_op:
        batch_op.drop_constraint("fk_cert_created_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_cert_organization_id", type_="foreignkey")
        batch_op.drop_column("created_by_user_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("certificate_authorities", schema=None) as batch_op:
        batch_op.drop_constraint("fk_ca_created_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_ca_organization_id", type_="foreignkey")
        batch_op.drop_column("created_by_user_id")
        batch_op.drop_column("organization_id")
