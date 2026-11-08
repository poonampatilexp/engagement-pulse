import io


def test_consultant_csv_upload_and_status(client, consultant_password):
    # Consultant login
    login_res = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    token = login_res.json().get("access_token") or login_res.json().get("access")

    # Get a project
    orgs = client.get("/api/organisations/", headers={"Authorization": f"Bearer {token}"}).json()
    acme_org = next(o for o in orgs if o["slug"] == "acme-health")
    projects = client.get(
        f"/api/organisations/{acme_org['id']}/projects/",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(projects) >= 1
    project_id = projects[0]["id"]

    # Upload sample CSV
    csv_content = b"title,severity,status,description,owner\nTest Risk,medium,open,Sample description,Test Owner\n"
    files = {"file": ("test_risks.csv", io.BytesIO(csv_content), "text/csv")}
    upload_res = client.post(
        f"/api/projects/{project_id}/csv-jobs/",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_res.status_code in [200, 201, 202]
    job_data = upload_res.json()
    assert "id" in job_data or "job_id" in job_data
    job_id = job_data.get("id") or job_data.get("job_id")

    # Check status endpoint
    status_res = client.get(
        f"/api/csv-jobs/{job_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "status" in status_data


def test_viewer_csv_upload_forbidden(client, viewer_password, consultant_password):
    # Find project using consultant
    c_login = client.post(
        "/api/auth/login/",
        json={"email": "consultant@engagementpulse.com", "password": consultant_password},
    )
    c_token = c_login.json().get("access_token") or c_login.json().get("access")
    orgs = client.get("/api/organisations/", headers={"Authorization": f"Bearer {c_token}"}).json()
    acme_org = next(o for o in orgs if o["slug"] == "acme-health")
    projects = client.get(
        f"/api/organisations/{acme_org['id']}/projects/",
        headers={"Authorization": f"Bearer {c_token}"},
    ).json()
    project_id = projects[0]["id"]

    # Viewer login
    v_login = client.post(
        "/api/auth/login/",
        json={"email": "viewer.acme@example.com", "password": viewer_password},
    )
    v_token = v_login.json().get("access_token") or v_login.json().get("access")

    # Viewer tries to upload -> 403 Forbidden
    csv_content = b"title,severity,status,description,owner\nTest Risk,medium,open,Sample,Owner\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    upload_res = client.post(
        f"/api/projects/{project_id}/csv-jobs/",
        files=files,
        headers={"Authorization": f"Bearer {v_token}"},
    )
    assert upload_res.status_code == 403

