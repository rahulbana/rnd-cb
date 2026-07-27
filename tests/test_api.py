from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_scenarios_endpoint():
    resp = client.get("/scenarios")
    assert resp.status_code == 200
    body = resp.json()
    assert "fraud" in body and body["fraud"]["task_type"] == "binary_classification"


def test_plan_endpoint():
    resp = client.post("/plan", json={"prompt": "loan default dataset with 8% default"})
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["task_type"] == "binary_classification"
    assert abs(spec["target"]["positive_rate"] - 0.08) < 1e-9


def test_generate_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.datasets_dir", tmp_path)
    resp = client.post(
        "/generate",
        json={
            "prompt": "fraud dataset with 1500 rows and 4% fraud rate",
            "formats": ["csv"],
            "full": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["rows"] >= 1500
    assert body["evaluation"]["ml_readiness_score"] is not None
    assert "csv" in body["exports"]
