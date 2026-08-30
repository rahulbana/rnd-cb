"""API end-to-end tests (spec sections 34, 37)."""


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_meta_lists_agents_and_tools(client):
    body = client.get("/api/v1/meta").json()
    assert len(body["agents"]) == 13
    assert any(t["name"] == "weather" for t in body["tools"])


def test_create_plan_and_derived_views(client):
    created = client.post("/api/v1/trips/from-text",
                          json={"text": "6 day trip to Paris, love food and art, budget $3000"})
    assert created.status_code == 201
    trip = created.json()
    tid = trip["trip_id"]

    planned = client.post(f"/api/v1/trips/{tid}/plan").json()
    assert planned["status"] == "planned"
    assert len(planned["itinerary"]) == 6

    budget = client.get(f"/api/v1/trips/{tid}/budget").json()
    assert budget["total_comfort"]["currency"] == "USD"

    mp = client.get(f"/api/v1/trips/{tid}/map").json()
    assert any(p["name"] == "Paris" for p in mp["points"])


def test_itinerary_reorder_persists(client):
    tid = client.post("/api/v1/trips/from-text",
                      json={"text": "3 day trip to Rome"}).json()["trip_id"]
    client.post(f"/api/v1/trips/{tid}/plan")
    itin = client.get(f"/api/v1/trips/{tid}/itinerary").json()
    itin.reverse()
    updated = client.patch(f"/api/v1/trips/{tid}/itinerary", json={"itinerary": itin}).json()
    assert updated[0]["day"] == itin[0]["day"]


def test_trip_not_found_returns_404(client):
    r = client.get("/api/v1/trips/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_auth_register_login_me(client):
    reg = client.post("/api/v1/auth/register",
                      json={"email": "a@b.com", "password": "password123"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@b.com"
    # duplicate registration rejected
    dup = client.post("/api/v1/auth/register",
                      json={"email": "a@b.com", "password": "password123"})
    assert dup.status_code == 409


def test_chat_is_grounded(client):
    tid = client.post("/api/v1/trips/from-text",
                      json={"text": "5 day trip to Tokyo, budget $2000"}).json()["trip_id"]
    client.post(f"/api/v1/trips/{tid}/plan")
    r = client.post("/api/v1/chat", json={"trip_id": tid, "message": "make it cheaper"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "optimize"
    assert "Tokyo" in body["reply"]  # grounded in trip context
