"""Add chunk text to chunks_meta (sparse/BM25 retrieval corpus)

Revision ID: 0002_chunk_text
Revises: 0001_initial
Create Date: 2026-09-06

Phase 5 keeps each chunk's text in Postgres so lexical (BM25 / full-text)
retrieval has a corpus alongside the dense vectors in the vector store.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_chunk_text"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks_meta",
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("chunks_meta", "text")
