def test_consultant_organisation_list(client, consultant_password):
    # Login as consultant
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    token = login_res.json().get("access_token") or login_res.json().get("access")

    res = client.get(
        "/api/organisations/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    orgs = res.json()
    assert len(orgs) >= 2
    org_slugs = [o["slug"] for o in orgs]
    assert "acme-health" in org_slugs


def test_client_viewer_organisation_isolation(client, viewer_password):
    # Login as viewer.acme
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "viewer.acme@example.com", "password": viewer_password},
    )
    token = login_res.json().get("access_token") or login_res.json().get("access")

    res = client.get(
        "/api/organisations/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    orgs = res.json()
    assert len(orgs) == 1
    assert orgs[0]["slug"] == "acme-health"


def test_unauthenticated_organisations_rejected(client):
    res = client.get("/api/organisations/")
    assert res.status_code == 401
