from app.dedup import canonical_url, deduplicate, title_similarity
from app.models.schemas import Source


def _src(url, title, cred=0.5):
    return Source(title=title, url=url, credibility=cred)


def test_canonical_strips_tracking_and_normalizes():
    a = canonical_url("http://www.Example.com/Path/?utm_source=x&b=2&a=1#frag")
    b = canonical_url("https://example.com/Path?a=1&b=2")
    assert a == b


def test_canonical_trailing_slash_and_scheme():
    assert canonical_url("https://a.com/x/") == canonical_url("http://a.com/x")


def test_title_similarity_bounds():
    assert title_similarity("hello world", "hello world") == 1.0
    assert title_similarity("", "x") == 0.0
    assert 0 < title_similarity("openai launches gpt", "openai launches gpt5") < 1


def test_dedup_removes_url_duplicates_keeps_first():
    sources = [
        _src("https://a.com/x?utm_source=1", "A", cred=0.9),
        _src("http://www.a.com/x/", "A dup", cred=0.4),
        _src("https://b.com/y", "B", cred=0.5),
    ]
    out = deduplicate(sources)
    urls = {s.url for s in out}
    assert len(out) == 2
    # first-seen (higher-cred) copy survives
    assert "https://a.com/x?utm_source=1" in urls


def test_dedup_removes_near_duplicate_titles():
    sources = [
        _src("https://a.com/1", "Nvidia beats earnings expectations for Q3"),
        _src("https://b.com/2", "Nvidia beats earnings expectations for Q3 again"),
    ]
    out = deduplicate(sources, title_threshold=0.7)
    assert len(out) == 1


def test_dedup_keeps_distinct():
    sources = [_src("https://a.com/1", "Apples"), _src("https://b.com/2", "Oranges")]
    assert len(deduplicate(sources)) == 2
