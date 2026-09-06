"""Seed a default user for the single-tenant org

Revision ID: 0003_seed_default_user
Revises: 0002_chunk_text
Create Date: 2026-09-06

Phase 7 persists conversations, whose ``user_id`` references ``users``. Until
real auth lands in Phase 8, seed one system user whose id equals the default
org id so conversations have a valid owner.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_seed_default_user"
down_revision: str | None = "0002_chunk_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("role", sa.String),
        sa.column("org_id", sa.String),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": _DEFAULT_ID,
                "email": "system@rag-platform.local",
                "hashed_password": "!",  # not a valid hash; cannot be logged into
                "role": "system",
                "org_id": _DEFAULT_ID,
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM users WHERE id = '{_DEFAULT_ID}'"))
