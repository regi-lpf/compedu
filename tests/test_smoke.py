from fastapi.testclient import TestClient

from api.index import app as vercel_app
from app.main import app


def test_health_and_frontend_served():
    assert vercel_app is app
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok"}
    index = client.get("/")
    assert index.status_code == 200 and "CompEdu" in index.text
    assert client.get("/style.css").status_code == 200
    assert client.get("/api.js").status_code == 200
    assert client.get("/script.js").status_code == 200

