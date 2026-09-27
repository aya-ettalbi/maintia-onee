def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_health(client):
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
