"""In-process smoke test: auth + article CRUD + search + export.

Runs without OpenAI/Chroma/sentence-transformers installed, exercising
the SQLite + hash-embedder + in-memory-vector fallbacks.
"""
import asyncio
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["DEBUG"] = "false"
os.environ["EMBEDDING_PROVIDER"] = "hash"

import httpx  # noqa: E402

from app.main import app  # noqa: E402


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as c:
            api = "/api/v1"

            # health
            r = await c.get("/health")
            assert r.status_code == 200, r.text
            print("health:", r.json())

            # register
            r = await c.post(
                f"{api}/auth/register",
                json={"email": "writer@example.com", "password": "supersecret1", "full_name": "Ada"},
            )
            assert r.status_code == 201, r.text
            token = r.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}

            # me
            r = await c.get(f"{api}/auth/me", headers=h)
            assert r.status_code == 200 and r.json()["email"] == "writer@example.com", r.text

            # login
            r = await c.post(
                f"{api}/auth/login",
                data={"username": "writer@example.com", "password": "supersecret1"},
            )
            assert r.status_code == 200, r.text

            # create articles
            ids = []
            for title, body in [
                ("Async Python Patterns", "How to use asyncio and coroutines effectively."),
                ("SEO for Developers", "Optimising technical blogs for search engines."),
            ]:
                r = await c.post(
                    f"{api}/articles",
                    headers=h,
                    json={
                        "title": title,
                        "body": body,
                        "summary": body[:40],
                        "keywords": ["python", "async"],
                        "tags": ["engineering"],
                        "ner_tags": [{"text": "Python", "type": "LANGUAGE"}],
                        "sources": [
                            {
                                "title": "Python asyncio docs",
                                "url": "https://docs.python.org/3/library/asyncio.html",
                                "type": "reference",
                            }
                        ],
                    },
                )
                assert r.status_code == 201, r.text
                ids.append(r.json()["id"])
            print("created articles:", ids)

            # list
            r = await c.get(f"{api}/articles", headers=h)
            assert r.status_code == 200 and len(r.json()) == 2, r.text

            # sources persisted on create
            r = await c.get(f"{api}/articles/{ids[0]}", headers=h)
            assert r.status_code == 200, r.text
            assert r.json()["sources"][0]["title"] == "Python asyncio docs", r.text
            print("sources persisted:", r.json()["sources"])

            # update
            r = await c.patch(
                f"{api}/articles/{ids[0]}", headers=h, json={"status": "published"}
            )
            assert r.status_code == 200 and r.json()["status"] == "published", r.text

            # semantic search
            r = await c.get(f"{api}/search", headers=h, params={"q": "asyncio coroutines"})
            assert r.status_code == 200, r.text
            print("search results:", [(x["article"]["title"], x["score"]) for x in r.json()])

            # export (md + docx + pdf if libs available)
            r = await c.get(f"{api}/articles/{ids[0]}/export", headers=h, params={"format": "md"})
            assert r.status_code == 200 and b"Async Python" in r.content, r.text
            assert b"## Sources" in r.content and b"asyncio" in r.content, r.text
            print("markdown export bytes:", len(r.content))

            # generation without key -> 503
            r = await c.post(
                f"{api}/generate", headers=h, json={"prompt": "Write about FastAPI"}
            )
            assert r.status_code == 503, r.text
            print("generate (no key) correctly returned 503")

            # unauthorized
            r = await c.get(f"{api}/articles")
            assert r.status_code == 401, r.text

    print("\nALL SMOKE TESTS PASSED ✅")


if __name__ == "__main__":
    asyncio.run(main())
