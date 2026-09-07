import json

from product_intel import Orchestrator
from product_intel.agents.web_ingestion import FixtureScraper
from product_intel.dashboard import render_dashboard


def _orch(sample_payload):
    return Orchestrator(scraper=FixtureScraper(payload=sample_payload))


def test_end_to_end_produces_plan_schema(sample_payload):
    report = _orch(sample_payload).run()
    d = report.to_dict()
    # top-level keys match the architecture plan (section 5)
    for key in ("product_summary", "core_strengths", "feature_gaps", "vnext_backlog"):
        assert key in d
    ps = d["product_summary"]
    assert ps["product_id"] == "PROD-9842"
    assert ps["total_reviews_analyzed"] == 26
    assert 0.0 <= ps["positive_sentiment_ratio"] <= 1.0


def test_strict_schema_omits_diagnostics(sample_payload):
    report = _orch(sample_payload).run()
    strict = report.to_dict(include_diagnostics=False)
    assert "diagnostics" not in strict
    assert "diagnostics" in report.to_dict(include_diagnostics=True)


def test_backlog_item_shape_matches_plan(sample_payload):
    report = _orch(sample_payload).run()
    item = report.to_dict()["vnext_backlog"][0]
    for key in ("ticket_id", "type", "priority", "title", "frequency_impact", "proposed_action"):
        assert key in item
    assert item["priority"] in ("P0", "P1", "P2")
    assert item["type"] in ("Defect / Bug", "Feature Enhancement")


def test_report_is_json_serializable(sample_payload):
    report = _orch(sample_payload).run()
    # must round-trip through JSON without error
    text = json.dumps(report.to_dict())
    assert json.loads(text)["product_summary"]["name"]


def test_stateful_run_retains_all_artifacts(sample_payload):
    state = _orch(sample_payload).run_stateful()
    assert state.ingested is not None
    assert state.sentiment is not None
    assert state.audit is not None
    assert state.defects is not None
    assert state.report is not None
    assert state.log  # progress log recorded


def test_dashboard_renders_html(sample_payload):
    report = _orch(sample_payload).run()
    html = render_dashboard(report)
    assert html.startswith("<!doctype html>")
    assert "AcousticPro Wireless ANC Headphones" in html
    assert "vNext Backlog" in html
    # no unescaped raw content that would break the document
    assert "<script>" not in html
