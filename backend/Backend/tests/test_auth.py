def test_admin_login(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "AdminTest123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
