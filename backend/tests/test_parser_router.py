"""Parser router: MIME routing and the logged fallback chain."""

from __future__ import annotations

import pytest

from app.adapters.parsers import ParserError, ParserRouter
from app.domain.models import ParsedDocument, TextBlock


class _AlwaysFails:
    name = "boom"

    def supports(self, mime_type: str) -> bool:
        return mime_type == "application/pdf"

    async def parse(self, data, *, filename, mime_type) -> ParsedDocument:
        raise RuntimeError("simulated parser failure")


class _AlwaysWorks:
    name = "ok"

    def supports(self, mime_type: str) -> bool:
        return mime_type == "application/pdf"

    async def parse(self, data, *, filename, mime_type) -> ParsedDocument:
        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=[TextBlock(text="ok", page=1)],
            page_count=1,
            parser_name=self.name,
        )


@pytest.mark.asyncio
async def test_fallback_chain_recovers_and_flags_used_fallback():
    router = ParserRouter([_AlwaysFails(), _AlwaysWorks()])
    parsed = await router.parse(b"x", filename="d.pdf", mime_type="application/pdf")
    assert parsed.parser_name == "ok"
    # Recovered via a non-primary parser -> recorded, never silent.
    assert parsed.used_fallback is True


@pytest.mark.asyncio
async def test_primary_success_is_not_flagged_as_fallback():
    router = ParserRouter([_AlwaysWorks(), _AlwaysFails()])
    parsed = await router.parse(b"x", filename="d.pdf", mime_type="application/pdf")
    assert parsed.parser_name == "ok"
    assert parsed.used_fallback is False


@pytest.mark.asyncio
async def test_no_parser_for_mime_raises():
    router = ParserRouter([_AlwaysWorks()])
    with pytest.raises(ParserError):
        await router.parse(b"x", filename="a.xyz", mime_type="application/x-weird")


@pytest.mark.asyncio
async def test_all_parsers_failing_raises():
    router = ParserRouter([_AlwaysFails()])
    with pytest.raises(ParserError):
        await router.parse(b"x", filename="d.pdf", mime_type="application/pdf")


def test_chain_for_orders_by_priority():
    a, b = _AlwaysWorks(), _AlwaysFails()
    router = ParserRouter([a, b])
    chain = router.chain_for("application/pdf")
    assert [p.name for p in chain] == ["ok", "boom"]
