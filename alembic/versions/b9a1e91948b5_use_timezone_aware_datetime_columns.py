"""use timezone-aware datetime columns

Revision ID: b9a1e91948b5
Revises: 0284d86b8ece
Create Date: 2026-04-13 13:18:19.790784

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9a1e91948b5"
down_revision: Union[str, Sequence[str], None] = "0284d86b8ece"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All datetime columns that need to become timezone-aware.
_COLUMNS = [
    ("audit_logs", "created_at"),
    ("certificate_authorities", "created_at"),
    ("certificate_authorities", "updated_at"),
    ("certificates", "created_at"),
    ("certificates", "updated_at"),
    ("certificates", "not_before"),
    ("certificates", "not_after"),
    ("certificates", "revoked_at"),
    ("crl_entries", "created_at"),
    ("crl_entries", "revocation_date"),
    ("organizations", "created_at"),
    ("organizations", "updated_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
]


_UPDATED_AT_COLUMNS = [
    ("certificate_authorities", "updated_at"),
    ("certificates", "updated_at"),
    ("organizations", "updated_at"),
    ("users", "updated_at"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for table, column in _COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(),
                type_=sa.DateTime(timezone=True),
            )

    # The original updated_at sa_column definitions omitted nullable=False,
    # so these columns were incorrectly nullable. Fix that now.
    for table, column in _UPDATED_AT_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
            )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column in _UPDATED_AT_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(),
                nullable=True,
            )

    for table, column in _COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(),
            )
