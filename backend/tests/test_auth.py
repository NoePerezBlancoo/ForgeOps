def test_login_returns_user_and_access_token(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@alpha.local", "password": "Admin123!"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
    assert response.json()["access_token"]
    assert response.cookies.get("forgeops_refresh")


def test_login_rejects_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@alpha.local", "password": "Wrong123!"}
    )
    assert response.status_code == 401
