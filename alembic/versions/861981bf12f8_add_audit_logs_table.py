"""Add audit_logs table

Revision ID: 861981bf12f8
Revises: b2f0c55c79a7
Create Date: 2026-02-02 11:19:53.210380

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "861981bf12f8"
down_revision: Union[str, Sequence[str], None] = "b2f0c55c79a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_ACTIONS = (
    "CA_CREATE",
    "CA_DELETE",
    "CA_EXPORT_PRIVATE_KEY",
    "CERT_CREATE",
    "CERT_REVOKE",
    "CERT_EXPORT_PRIVATE_KEY",
    "LOGIN_SUCCESS",
    "LOGIN_FAILURE",
    "USER_CREATE",
    "USER_UPDATE",
    "ORG_CREATE",
    "ORG_DELETE",
    "ORG_ADD_USER",
    "ORG_REMOVE_USER",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(*AUDIT_ACTIONS, name="auditaction"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_audit_logs_action"), ["action"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_audit_logs_created_at"),
            ["created_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_audit_logs_organization_id"),
            ["organization_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_audit_logs_user_id"),
            ["user_id"],
            unique=False,
        )

    with op.batch_alter_table("certificate_authorities", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=True)

    with op.batch_alter_table("certificates", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=True)

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=True)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=False)

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=False)

    with op.batch_alter_table("certificates", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=False)

    with op.batch_alter_table("certificate_authorities", schema=None) as batch_op:
        batch_op.alter_column("updated_at", existing_type=sa.DATETIME(), nullable=False)

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_logs_user_id"))
        batch_op.drop_index(batch_op.f("ix_audit_logs_organization_id"))
        batch_op.drop_index(batch_op.f("ix_audit_logs_created_at"))
        batch_op.drop_index(batch_op.f("ix_audit_logs_action"))

    op.drop_table("audit_logs")
