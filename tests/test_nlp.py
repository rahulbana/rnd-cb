from collections import Counter

from product_intel import nlp


def test_tokenize_removes_stopwords():
    toks = nlp.tokenize("The battery is very good and reliable")
    assert "battery" in toks and "reliable" in toks
    assert "the" not in toks and "is" not in toks


def test_sentiment_positive_and_negative():
    assert nlp.sentiment_score("Amazing sound, excellent and comfortable") > 0.3
    assert nlp.sentiment_score("Terrible, broken and disappointing") < -0.3


def test_sentiment_negation_flip():
    assert nlp.sentiment_score("not comfortable") < 0


def test_sentiment_neutral_when_no_lexicon_hits():
    assert nlp.sentiment_score("I bought this yesterday") == 0.0


def test_normalize_sentiment_range():
    assert nlp.normalize_sentiment(-1.0) == 0.0
    assert nlp.normalize_sentiment(1.0) == 1.0
    assert nlp.normalize_sentiment(0.0) == 0.5


def test_assign_topic_picks_best_match():
    topics = {"Battery": ["battery", "charge"], "Sound": ["sound", "bass"]}
    assert nlp.assign_topic("battery drains fast", topics, "Other") == "Battery"
    assert nlp.assign_topic("the bass and sound", topics, "Other") == "Sound"
    assert nlp.assign_topic("nothing relevant", topics, "Other") == "Other"


def test_cosine_bounds():
    a = nlp.bag_of_words("battery charge power")
    b = nlp.bag_of_words("battery charge power")
    assert abs(nlp.cosine(a, b) - 1.0) < 1e-9
    assert nlp.cosine(a, Counter()) == 0.0


def test_agglomerative_cluster_groups_similar():
    vecs = [
        nlp.bag_of_words("battery charge power hours"),
        nlp.bag_of_words("battery charge power drain"),
        nlp.bag_of_words("sound bass treble audio"),
    ]
    clusters = nlp.agglomerative_cluster(vecs, threshold=0.2)
    # the two battery vectors should land together, sound separate
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]
