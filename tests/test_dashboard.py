from fastapi.testclient import TestClient
from app.main import app

def test_dashboard_requires_auth():
    with TestClient(app) as client:
        assert client.get("/admin").status_code==401

def test_dashboard_renders():
    with TestClient(app) as client:
        response=client.get("/admin",auth=("admin","a"*20))
        assert response.status_code==200
        assert "Booking Control" in response.text
