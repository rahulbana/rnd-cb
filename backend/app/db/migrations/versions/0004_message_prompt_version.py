"""Add prompt_version to messages (RAG traceability)

Revision ID: 0004_message_prompt_version
Revises: 0003_seed_default_user
Create Date: 2026-09-06

Phase 9 records the prompt version on each assistant turn so a bad answer can
be traced to its exact retrieved chunks (citations), reranker scores, provider,
and prompt version.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_message_prompt_version"
down_revision: str | None = "0003_seed_default_user"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages", sa.Column("prompt_version", sa.String(length=32), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("messages", "prompt_version")
