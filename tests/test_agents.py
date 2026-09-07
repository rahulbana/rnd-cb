import pytest

from product_intel.agents import (
    DefectDiagnosticAgent,
    FeatureAuditAgent,
    RoadmapSynthesisAgent,
    SentimentTopicAgent,
    WebIngestionAgent,
)
from product_intel.agents.web_ingestion import FixtureScraper
from product_intel.llm import OfflineLLM
from product_intel.schemas import DefectCategory, Priority


# --------------------------------------------------------------------------- #
# Agent 1 - ingestion
# --------------------------------------------------------------------------- #
def test_ingestion_normalizes_and_validates(sample_payload):
    agent = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload))
    ingested = agent.run()
    assert ingested.metadata.name == "AcousticPro Wireless ANC Headphones"
    assert len(ingested.reviews) == 28
    # dates normalized to ISO
    assert all(r.timestamp is None or r.timestamp[4] == "-" for r in ingested.reviews)


def test_ingestion_requires_name():
    agent = WebIngestionAgent(scraper=FixtureScraper(payload={"metadata": {}, "reviews": []}))
    with pytest.raises(ValueError):
        agent.run()


def test_ingestion_dedupes_identical_bodies():
    payload = {
        "metadata": {"product_id": "X", "name": "Widget"},
        "reviews": [
            {"rating": 5, "body": "Great widget"},
            {"rating": 5, "body": "Great widget"},
            {"rating": 1, "body": "Bad widget"},
        ],
    }
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=payload)).run()
    assert len(ingested.reviews) == 2


def test_ingestion_normalizes_various_date_formats():
    payload = {
        "metadata": {"product_id": "X", "name": "Widget"},
        "reviews": [
            {"rating": 5, "body": "a", "date": "March 5, 2023"},
            {"rating": 5, "body": "b", "date": "05/03/2023"},
            {"rating": 5, "body": "c", "date": "Reviewed in the US on 12 April 2022"},
        ],
    }
    reviews = WebIngestionAgent(scraper=FixtureScraper(payload=payload)).run().reviews
    assert reviews[0].timestamp == "2023-03-05"
    assert reviews[2].timestamp == "2022-04-12"


# --------------------------------------------------------------------------- #
# Agent 2 - sentiment & clustering
# --------------------------------------------------------------------------- #
def test_sentiment_filters_courier_noise(sample_payload):
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload)).run()
    report = SentimentTopicAgent().run(ingested)
    assert report.filtered_out == 2  # two courier/shipping reviews
    assert report.total_reviews_analyzed == 26
    assert 0.0 <= report.positive_sentiment_ratio <= 1.0


def test_sentiment_clusters_have_expected_topics(sample_payload):
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload)).run()
    report = SentimentTopicAgent().run(ingested)
    names = {c.name for c in report.clusters}
    assert "Noise Cancellation" in names
    assert "Connectivity" in names
    # positive/neutral/negative sum equals mention frequency per cluster
    for c in report.clusters:
        assert c.positive + c.neutral + c.negative == c.mention_frequency


# --------------------------------------------------------------------------- #
# Agent 3 - feature audit
# --------------------------------------------------------------------------- #
def test_feature_audit_splits_strengths_and_gaps(sample_payload):
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload)).run()
    sentiment = SentimentTopicAgent().run(ingested)
    audit = FeatureAuditAgent(OfflineLLM()).run(ingested.metadata, sentiment)
    strength_features = {s.feature for s in audit.core_strengths}
    gap_features = {g.feature for g in audit.feature_gaps}
    assert "Active Noise Cancellation" in strength_features
    assert "Multipoint Bluetooth Pairing" in gap_features
    # a feature is never both a strength and a gap
    assert strength_features.isdisjoint(gap_features)


# --------------------------------------------------------------------------- #
# Agent 4 - defects
# --------------------------------------------------------------------------- #
def test_defect_diagnostics_dedupes_and_ranks(sample_payload):
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload)).run()
    log = DefectDiagnosticAgent().run(ingested)
    titles = [d.title for d in log.defects]
    assert "Bluetooth multipoint handoff disconnects" in titles
    # each defect signature appears once (deduped)
    assert len(titles) == len(set(titles))
    # sorted by severity descending
    sevs = [d.severity for d in log.defects]
    assert sevs == sorted(sevs, reverse=True)
    # top defect is the most severe functional blocker
    assert log.defects[0].category == DefectCategory.FUNCTIONAL_BLOCKER
    assert log.defects[0].defect_id == "DEF-001"


# --------------------------------------------------------------------------- #
# Agent 5 - roadmap
# --------------------------------------------------------------------------- #
def test_roadmap_assigns_priorities_and_tickets(sample_payload):
    ingested = WebIngestionAgent(scraper=FixtureScraper(payload=sample_payload)).run()
    sentiment = SentimentTopicAgent().run(ingested)
    llm = OfflineLLM()
    audit = FeatureAuditAgent(llm).run(ingested.metadata, sentiment)
    defects = DefectDiagnosticAgent().run(ingested).defects
    backlog = RoadmapSynthesisAgent(llm).run(defects, audit, sentiment)

    assert backlog, "expected at least one backlog item"
    # ticket ids are sequential from VNXT-101
    assert backlog[0].ticket_id == "VNXT-101"
    # the highest-priority item is a P0
    assert backlog[0].priority == Priority.P0
    # every item has a user story and acceptance criteria
    for item in backlog:
        assert item.user_story
        assert item.acceptance_criteria
        assert item.rice is not None
    # priorities are globally ordered P0 -> P1 -> P2
    order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2}
    ranks = [order[i.priority] for i in backlog]
    assert ranks == sorted(ranks)
