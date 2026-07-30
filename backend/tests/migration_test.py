"""Verify the additive startup migration repairs an older DB schema."""
import asyncio
import os
import tempfile

DB_PATH = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["DEBUG"] = "false"

import sqlite3  # noqa: E402


def make_old_schema() -> None:
    """Create an 'articles' table WITHOUT the newer columns (sources)."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255),
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN,
            created_at DATETIME
        );
        CREATE TABLE articles (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36),
            prompt TEXT,
            title VARCHAR(512),
            body TEXT,
            summary TEXT,
            seo_description TEXT,
            keywords JSON,
            sentiment VARCHAR(32),
            tags JSON,
            ner_tags JSON,
            status VARCHAR(32),
            created_at DATETIME,
            updated_at DATETIME
        );
        INSERT INTO articles (id, user_id, title, body, keywords, tags, ner_tags)
        VALUES ('old-1', 'u1', 'Legacy article', 'body', '[]', '[]', '[]');
        """
    )
    conn.commit()
    conn.close()


async def main() -> None:
    make_old_schema()

    from app.core.database import SessionLocal, init_db
    from app.models.article import Article

    await init_db()  # should ALTER TABLE to add 'sources'

    # Column now exists: legacy row reads back with default [] sources.
    async with SessionLocal() as s:
        legacy = await s.get(Article, "old-1")
        assert legacy is not None, "legacy row missing"
        assert legacy.sources == [], f"expected [] got {legacy.sources!r}"

        # And a new insert with sources succeeds (the original 500 error).
        art = Article(
            id="new-1",
            user_id="u1",
            title="New one",
            body="hello",
            sources=[{"title": "Example", "url": "https://example.com", "type": "reference"}],
        )
        s.add(art)
        await s.commit()

    async with SessionLocal() as s:
        art = await s.get(Article, "new-1")
        assert art.sources[0]["title"] == "Example", art.sources

    print("MIGRATION TEST PASSED ✅  (sources column added, insert works)")


if __name__ == "__main__":
    asyncio.run(main())
