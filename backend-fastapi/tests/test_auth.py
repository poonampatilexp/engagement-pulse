def test_login_success_and_me(client, consultant_password):
    # Test consultant login
    res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data or "access" in data
    assert "refresh_token" in data or "refresh" in data
    token = data.get("access_token") or data.get("access")

    # Test /api/auth/me/
    me_res = client.get(
        "/api/auth/me/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "consultant@engagementpulse.com"
    assert me_data["role"] == "consultant"


def test_login_invalid_credentials(client):
    res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "detail" in res.json()


def test_refresh_token_flow(client, viewer_password):
    # Login to obtain tokens
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "viewer.acme@example.com", "password": viewer_password},
    )
    assert login_res.status_code == 200
    refresh_token = login_res.json().get("refresh_token") or login_res.json().get("refresh")

    # Refresh
    refresh_res = client.post(
        "/api/auth/refresh/",
        json={"refresh": refresh_token},
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()
    assert "access" in refreshed_data or "access_token" in refreshed_data

    # Invalid refresh token
    bad_res = client.post(
        "/api/auth/refresh/",
        json={"refresh": "invalid.jwt.token"},
    )
    assert bad_res.status_code == 401


def test_logout_and_ws_ticket(client, consultant_password):
    # Login
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    token = login_res.json().get("access_token") or login_res.json().get("access")

    # Obtain single-use WebSocket ticket
    ticket_res = client.post(
        "/api/auth/ws-ticket/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ticket_res.status_code == 201
    assert "ticket" in ticket_res.json()
    assert ticket_res.json()["expires_in"] == 30

    # Logout
    logout_res = client.post(
        "/api/auth/logout/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
