from app.credibility import classify_domain, extract_domain, score_source


def test_extract_domain_strips_www():
    assert extract_domain("https://www.reuters.com/x") == "reuters.com"


def test_classify_known_tiers():
    assert classify_domain("arxiv.org") == "peer_reviewed"
    assert classify_domain("reuters.com") == "established_press"
    assert classify_domain("medium.com") == "blog_or_ugc"


def test_classify_tld_signals():
    assert classify_domain("nsf.gov") == "government"
    assert classify_domain("mit.edu") == "peer_reviewed"
    assert classify_domain("random-startup.io") == "unknown"


def test_score_ordering_press_beats_blog():
    press = score_source(url="https://reuters.com/a")
    blog = score_source(url="https://medium.com/@x/a")
    assert press > blog


def test_score_bounded_0_1():
    s = score_source(url="https://arxiv.org/abs/1234", backend="arxiv",
                     published="2025-01-01", has_full_content=True)
    assert 0.0 <= s <= 1.0
    assert s > 0.9


def test_arxiv_backend_lifts_unknown_domain():
    s = score_source(url="https://some-mirror.net/paper", backend="arxiv")
    assert s > 0.7


def test_stale_content_penalized():
    fresh = score_source(url="https://x.com/a", published="2025-06-01")
    stale = score_source(url="https://x.com/a", published="2005-06-01")
    assert fresh > stale
