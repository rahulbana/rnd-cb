from app.models.schemas import SearchHit, Source


def test_id_is_derived_from_url_and_is_distinct():
    a = Source(title="A", url="https://a.com/x")
    b = Source(title="B", url="https://b.com/y")
    assert a.id and b.id
    assert a.id != b.id, "distinct URLs must yield distinct ids"


def test_id_is_stable_for_same_url():
    a = Source(title="A", url="https://a.com/x")
    b = Source(title="different title", url="https://a.com/x")
    assert a.id == b.id, "id depends only on url"


def test_explicit_id_preserved():
    s = Source(id="custom", title="A", url="https://a.com/x")
    assert s.id == "custom"


def test_from_hit_derives_id():
    hit = SearchHit(title="T", url="https://t.com", snippet="s", backend="tavily")
    src = Source.from_hit(hit)
    assert src.id
    assert src.backend == "tavily"
