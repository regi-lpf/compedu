from fastapi.testclient import TestClient

from app.main import app


def test_health_and_frontend_served():
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok"}
    index = client.get("/")
    assert index.status_code == 200 and "CompEdu" in index.text
    assert client.get("/style.css").status_code == 200
    assert client.get("/api.js").status_code == 200
