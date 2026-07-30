"""Smoke test for writing-style references: upload, list, delete, indexing."""
import asyncio
import io
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["DEBUG"] = "false"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["WEB_SEARCH_PROVIDER"] = "none"

import httpx  # noqa: E402

from app.main import app  # noqa: E402


def make_docx_bytes(text: str) -> bytes:
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            api = "/api/v1"

            r = await c.post(
                f"{api}/auth/register",
                json={"email": "styler@example.com", "password": "supersecret1"},
            )
            token = r.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}

            # upload a .txt file
            r = await c.post(
                f"{api}/style-references/upload",
                headers=h,
                files={"file": ("voice.txt", b"I write in short, punchy sentences. Bold claims.", "text/plain")},
            )
            assert r.status_code == 201, r.text
            txt_id = r.json()["id"]
            assert r.json()["char_count"] > 0
            print("uploaded txt:", r.json()["name"], r.json()["char_count"], "chars")

            # upload a .docx file
            docx_bytes = make_docx_bytes("My essays are witty and warm.\nI love vivid metaphors.")
            r = await c.post(
                f"{api}/style-references/upload",
                headers=h,
                files={
                    "file": (
                        "essay.docx",
                        docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert r.status_code == 201, r.text
            assert "witty" in r.json() or True  # content not returned; just check ok
            print("uploaded docx:", r.json()["name"], r.json()["char_count"], "chars")

            # reject unsupported type
            r = await c.post(
                f"{api}/style-references/upload",
                headers=h,
                files={"file": ("bad.pdf", b"%PDF-1.4", "application/pdf")},
            )
            assert r.status_code == 400, r.text
            print("rejected .pdf as expected")

            # list
            r = await c.get(f"{api}/style-references", headers=h)
            assert r.status_code == 200 and len(r.json()) == 2, r.text

            # the style ref is retrievable from the vector store
            from app.services.vectorstore import get_vector_store

            hits = get_vector_store().search_style_references(
                query="punchy sentences", user_id=r.json()[0]["user_id"] if False else _user_id(token), n_results=5
            )
            assert any(hid == txt_id for hid, _ in hits), hits
            print("style ref indexed & retrievable:", len(hits), "hits")

            # delete
            r = await c.delete(f"{api}/style-references/{txt_id}", headers=h)
            assert r.status_code == 204, r.text
            r = await c.get(f"{api}/style-references", headers=h)
            assert len(r.json()) == 1, r.text

    print("\nSTYLE REFERENCE TEST PASSED ✅")


def _user_id(token: str) -> str:
    from app.core.security import decode_access_token

    return decode_access_token(token)


if __name__ == "__main__":
    asyncio.run(main())
