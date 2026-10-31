import pytest
from django.urls import reverse
from rest_framework import status
from apps.organisations.models import Organisation
from apps.projects.models import Project, Risk, RiskSeverity, RiskStatus


@pytest.mark.django_db
class TestProjectEndpoints:

    def test_unauthenticated_access_denied(self, api_client, seeded_data):
        org_id = seeded_data['org_acme'].id
        proj_id = seeded_data['project_acme'].id

        # List/Create
        assert api_client.get(f'/api/organisations/{org_id}/projects/').status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(f'/api/organisations/{org_id}/projects/', {'name': 'P'}).status_code == status.HTTP_401_UNAUTHORIZED

        # Detail
        assert api_client.get(f'/api/projects/{proj_id}/').status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.patch(f'/api/projects/{proj_id}/', {'name': 'P2'}).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(f'/api/projects/{proj_id}/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_consultant_access_multiple_organisations(self, consultant_client, seeded_data):
        """Consultant can view and create projects in all assigned organisations."""
        acme_id = seeded_data['org_acme'].id
        globex_id = seeded_data['org_globex'].id

        # List Acme projects
        res_acme = consultant_client.get(f'/api/organisations/{acme_id}/projects/')
        assert res_acme.status_code == status.HTTP_200_OK
        assert len(res_acme.data) >= 1

        # List Globex projects
        res_globex = consultant_client.get(f'/api/organisations/{globex_id}/projects/')
        assert res_globex.status_code == status.HTTP_200_OK
        assert len(res_globex.data) >= 1

        # Create in Acme
        create_res = consultant_client.post(
            f'/api/organisations/{acme_id}/projects/',
            {'name': 'New Acme Project'},
            format='json'
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        assert create_res.data['name'] == 'New Acme Project'
        assert create_res.data['risk_score'] == 0

    def test_consultant_crud_lifecycle(self, consultant_client, seeded_data):
        """Consultant can create, retrieve, update, and delete projects."""
        acme_id = seeded_data['org_acme'].id

        # 1. Create
        create_res = consultant_client.post(
            f'/api/organisations/{acme_id}/projects/',
            {'name': 'Lifecycle Project'},
            format='json'
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        proj_id = create_res.data['id']

        # 2. Retrieve
        get_res = consultant_client.get(f'/api/projects/{proj_id}/')
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.data['name'] == 'Lifecycle Project'

        # 3. Update (PATCH)
        patch_res = consultant_client.patch(
            f'/api/projects/{proj_id}/',
            {'name': 'Renamed Project'},
            format='json'
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data['name'] == 'Renamed Project'

        # 4. Delete
        del_res = consultant_client.delete(f'/api/projects/{proj_id}/')
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        # Confirm deleted
        assert consultant_client.get(f'/api/projects/{proj_id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_client_viewer_read_only_permissions(self, viewer_acme_client, seeded_data):
        """Client viewer can view their own organisation projects, but write operations are forbidden (403)."""
        acme_id = seeded_data['org_acme'].id
        proj_id = seeded_data['project_acme'].id

        # 1. Read is allowed
        res_list = viewer_acme_client.get(f'/api/organisations/{acme_id}/projects/')
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.data) >= 1

        res_detail = viewer_acme_client.get(f'/api/projects/{proj_id}/')
        assert res_detail.status_code == status.HTTP_200_OK

        # 2. Create is forbidden (403)
        res_create = viewer_acme_client.post(
            f'/api/organisations/{acme_id}/projects/',
            {'name': 'Forbidden Project'},
            format='json'
        )
        assert res_create.status_code == status.HTTP_403_FORBIDDEN

        # 3. Update is forbidden (403)
        res_patch = viewer_acme_client.patch(
            f'/api/projects/{proj_id}/',
            {'name': 'Forbidden Edit'},
            format='json'
        )
        assert res_patch.status_code == status.HTTP_403_FORBIDDEN

        # 4. Delete is forbidden (403)
        res_del = viewer_acme_client.delete(f'/api/projects/{proj_id}/')
        assert res_del.status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_isolation_returns_404_for_inaccessible_resources(
        self, viewer_acme_client, consultant_client, seeded_data
    ):
        globex_id = seeded_data['org_globex'].id
        globex_proj_id = seeded_data['project_globex'].id

        # Acme viewer trying to list or view Globex projects receives 404
        assert viewer_acme_client.get(f'/api/organisations/{globex_id}/projects/').status_code == status.HTTP_404_NOT_FOUND
        assert viewer_acme_client.get(f'/api/projects/{globex_proj_id}/').status_code == status.HTTP_404_NOT_FOUND

        # Unassigned third organisation
        unassigned_org = Organisation.objects.create(name='Other Org', slug='other-org')
        unassigned_proj = Project.objects.create(organisation=unassigned_org, name='Other Proj')

        # Consultant not assigned to 'other-org' receives 404
        assert consultant_client.get(f'/api/organisations/{unassigned_org.id}/projects/').status_code == status.HTTP_404_NOT_FOUND
        assert consultant_client.get(f'/api/projects/{unassigned_proj.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_prevention_of_client_supplied_risk_score(self, consultant_client, seeded_data):
        """Clients cannot arbitrarily override the risk_score field."""
        acme_id = seeded_data['org_acme'].id

        # Attempt to create with forged risk_score
        create_res = consultant_client.post(
            f'/api/organisations/{acme_id}/projects/',
            {'name': 'Score Test Project', 'risk_score': 99},
            format='json'
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        assert create_res.data['risk_score'] == 0

        proj_id = create_res.data['id']

        # Attempt to patch risk_score directly
        patch_res = consultant_client.patch(
            f'/api/projects/{proj_id}/',
            {'risk_score': 77},
            format='json'
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data['risk_score'] == 0


@pytest.mark.django_db
class TestRiskEndpoints:

    def test_unauthenticated_risk_access_denied(self, api_client, seeded_data):
        proj_id = seeded_data['project_acme'].id
        risk = Risk.objects.create(project=seeded_data['project_acme'], title='R')

        assert api_client.get(f'/api/projects/{proj_id}/risks/').status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.post(f'/api/projects/{proj_id}/risks/', {'title': 'R2'}).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(f'/api/risks/{risk.id}/').status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.patch(f'/api/risks/{risk.id}/', {'title': 'R3'}).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(f'/api/risks/{risk.id}/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_risk_crud_and_automatic_score_recalculation(self, consultant_client, seeded_data):
        """Tests adding, updating, and deleting risks with automatic project score updates."""
        proj = seeded_data['project_acme']
        proj_id = proj.id

        # 1. Project starts with score 0
        get_proj = consultant_client.get(f'/api/projects/{proj_id}/')
        assert get_proj.data['risk_score'] == 0

        # 2. Add High (3) / Open (3) risk -> expected project score = 9
        add_res1 = consultant_client.post(
            f'/api/projects/{proj_id}/risks/',
            {
                'title': 'High Open Risk',
                'description': 'Impacting critical path',
                'severity': RiskSeverity.HIGH,
                'status': RiskStatus.OPEN,
                'owner': 'Lead Architect'
            },
            format='json'
        )
        assert add_res1.status_code == status.HTTP_201_CREATED
        risk1_id = add_res1.data['id']

        proj_after_r1 = consultant_client.get(f'/api/projects/{proj_id}/')
        assert proj_after_r1.data['risk_score'] == 9

        # 3. Add Medium (2) / Mitigating (2) risk -> expected project score = 9 + 4 = 13
        add_res2 = consultant_client.post(
            f'/api/projects/{proj_id}/risks/',
            {
                'title': 'Medium Mitigating Risk',
                'severity': RiskSeverity.MEDIUM,
                'status': RiskStatus.MITIGATING,
                'owner': 'DevOps Lead'
            },
            format='json'
        )
        assert add_res2.status_code == status.HTTP_201_CREATED

        proj_after_r2 = consultant_client.get(f'/api/projects/{proj_id}/')
        assert proj_after_r2.data['risk_score'] == 13

        # 4. Update Risk 1 to Closed (0) -> expected score = 0 + 4 = 4
        patch_res = consultant_client.patch(
            f'/api/risks/{risk1_id}/',
            {'status': RiskStatus.CLOSED},
            format='json'
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data['status'] == RiskStatus.CLOSED

        proj_after_patch = consultant_client.get(f'/api/projects/{proj_id}/')
        assert proj_after_patch.data['risk_score'] == 4

        # 5. Delete Risk 1 -> remaining score still 4
        del_res1 = consultant_client.delete(f'/api/risks/{risk1_id}/')
        assert del_res1.status_code == status.HTTP_204_NO_CONTENT

        proj_after_del = consultant_client.get(f'/api/projects/{proj_id}/')
        assert proj_after_del.data['risk_score'] == 4

    def test_client_viewer_read_only_risks(self, viewer_acme_client, seeded_data):
        """Client viewer can view risks in their project, but write operations are forbidden (403)."""
        proj = seeded_data['project_acme']
        risk = Risk.objects.create(
            project=proj,
            title='Acme Risk',
            severity=RiskSeverity.LOW,
            status=RiskStatus.OPEN
        )

        # 1. Read list and detail
        assert viewer_acme_client.get(f'/api/projects/{proj.id}/risks/').status_code == status.HTTP_200_OK
        assert viewer_acme_client.get(f'/api/risks/{risk.id}/').status_code == status.HTTP_200_OK

        # 2. Write operations are forbidden (403)
        assert viewer_acme_client.post(
            f'/api/projects/{proj.id}/risks/',
            {'title': 'Forbidden Risk', 'severity': 'low', 'status': 'open'},
            format='json'
        ).status_code == status.HTTP_403_FORBIDDEN

        assert viewer_acme_client.patch(
            f'/api/risks/{risk.id}/',
            {'title': 'Modified Title'},
            format='json'
        ).status_code == status.HTTP_403_FORBIDDEN

        assert viewer_acme_client.delete(f'/api/risks/{risk.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_isolation_on_risks_returns_404(self, viewer_acme_client, seeded_data):
        """Risks belonging to other organisations return 404."""
        globex_proj = seeded_data['project_globex']
        globex_risk = Risk.objects.create(
            project=globex_proj,
            title='Globex Secret Risk',
            severity=RiskSeverity.HIGH,
            status=RiskStatus.OPEN
        )

        # Acme client viewer requesting Globex project risks or risk detail
        assert viewer_acme_client.get(f'/api/projects/{globex_proj.id}/risks/').status_code == status.HTTP_404_NOT_FOUND
        assert viewer_acme_client.get(f'/api/risks/{globex_risk.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_validation_of_severity_and_status(self, consultant_client, seeded_data):
        """Rejects invalid severity or status choices with 400 Bad Request."""
        proj_id = seeded_data['project_acme'].id

        # Invalid severity
        res_sev = consultant_client.post(
            f'/api/projects/{proj_id}/risks/',
            {'title': 'Invalid Sev', 'severity': 'apocalyptic', 'status': 'open'},
            format='json'
        )
        assert res_sev.status_code == status.HTTP_400_BAD_REQUEST
        assert 'severity' in res_sev.data

        # Invalid status
        res_stat = consultant_client.post(
            f'/api/projects/{proj_id}/risks/',
            {'title': 'Invalid Status', 'severity': 'medium', 'status': 'postponed'},
            format='json'
        )
        assert res_stat.status_code == status.HTTP_400_BAD_REQUEST
        assert 'status' in res_stat.data

    def test_prevention_of_risk_project_alteration(self, consultant_client, seeded_data):
        """Updating a risk cannot silently reassign it to another project."""
        p1 = seeded_data['project_acme']
        p2 = seeded_data['project_globex']

        risk = Risk.objects.create(project=p1, title='P1 Risk', severity=RiskSeverity.LOW, status=RiskStatus.OPEN)

        patch_res = consultant_client.patch(
            f'/api/risks/{risk.id}/',
            {'project': p2.id, 'title': 'Updated Title'},
            format='json'
        )
        assert patch_res.status_code == status.HTTP_200_OK
        risk.refresh_from_db()
        assert risk.project_id == p1.id
        assert risk.title == 'Updated Title'

