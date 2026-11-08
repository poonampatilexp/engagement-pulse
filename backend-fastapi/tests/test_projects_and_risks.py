def test_list_projects_and_risks(client, consultant_password):
    # Consultant login
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    assert login_res.status_code == 200
    token = login_res.json().get("access_token") or login_res.json().get("access")

    # Get organisations
    orgs_res = client.get(
        "/api/organisations/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert orgs_res.status_code == 200
    orgs = orgs_res.json()
    acme_org = next(o for o in orgs if o["slug"] == "acme-health")

    # List projects for Acme Health
    proj_res = client.get(
        f"/api/organisations/{acme_org['id']}/projects/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert proj_res.status_code == 200
    projects = proj_res.json()
    assert isinstance(projects, list)
    if projects:
        project_id = projects[0]["id"]
        # List risks for that project
        risks_res = client.get(
            f"/api/projects/{project_id}/risks/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert risks_res.status_code == 200
        assert isinstance(risks_res.json(), list)


def test_viewer_cannot_update_risk(client, consultant_password, viewer_password):
    # Get consultant token to find a risk ID
    c_login = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    c_token = c_login.json().get("access_token") or c_login.json().get("access")
    orgs = client.get("/api/organisations/", headers={"Authorization": f"Bearer {c_token}"}).json()
    acme_org = next(o for o in orgs if o["slug"] == "acme-health")
    projects = client.get(f"/api/organisations/{acme_org['id']}/projects/", headers={"Authorization": f"Bearer {c_token}"}).json()
    if not projects:
        return
    risks = client.get(f"/api/projects/{projects[0]['id']}/risks/", headers={"Authorization": f"Bearer {c_token}"}).json()
    if not risks:
        return
    risk_id = risks[0]["id"]

    # Viewer login
    v_login = client.post(
        "/api/auth/login/",
        json={"email": "viewer.acme@example.com", "password": viewer_password},
    )
    v_token = v_login.json().get("access_token") or v_login.json().get("access")

    # Viewer tries to PATCH risk -> should be 403 Forbidden
    patch_res = client.patch(
        f"/api/risks/{risk_id}/",
        json={"status": "mitigating"},
        headers={"Authorization": f"Bearer {v_token}"},
    )
    assert patch_res.status_code == 403
