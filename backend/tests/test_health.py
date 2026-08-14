from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_responds():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Sales Readiness Intelligence" in response.json()["message"]


def test_health_reports_ok_and_db_connectivity():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["database_error"] is None
