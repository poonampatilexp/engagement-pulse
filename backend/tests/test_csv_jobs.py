import uuid
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from apps.organisations.models import Organisation, ConsultantOrganisationAccess
from apps.projects.models import Project, CSVImportJob, JobStatus
from apps.users.models import User, UserRole


@pytest.mark.django_db
class TestCSVUploadEndpoints:
    def test_unauthenticated_upload_rejected(self, api_client, seeded_data):
        project = seeded_data['project_acme']
        csv_file = SimpleUploadedFile("risks.csv", b"title,severity\nRisk 1,high\n", content_type="text/csv")
        response = api_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': csv_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_client_viewer_upload_forbidden(self, viewer_acme_client, seeded_data):
        project = seeded_data['project_acme']
        csv_file = SimpleUploadedFile("risks.csv", b"title,severity\nRisk 1,high\n", content_type="text/csv")
        response = viewer_acme_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': csv_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'consultant' in response.data['detail'].lower()

    def test_consultant_upload_valid_csv_creates_queued_job(self, consultant_client, seeded_data):
        project = seeded_data['project_acme']
        csv_content = b"title,description,severity,status,owner\nDatabase Latency,Query issues,high,open,DB Team\n"
        csv_file = SimpleUploadedFile("import_risks.csv", csv_content, content_type="text/csv")

        response = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert 'id' in data
        assert data['status'] == JobStatus.QUEUED
        assert data['filename'] == "import_risks.csv"
        assert data['project'] == project.id
        assert data['total_rows'] == 0
        assert data['error_details'] == {}

        # Verify job is saved in database
        job = CSVImportJob.objects.get(id=data['id'])
        assert job.status == JobStatus.QUEUED
        assert job.project == project
        assert job.created_by == seeded_data['consultant']

    def test_consultant_multiple_uploads_create_distinct_jobs(self, consultant_client, seeded_data):
        project = seeded_data['project_acme']
        csv_content = b"title,description,severity,status,owner\nSame Risk,Desc,low,open,Owner\n"

        # First upload
        file1 = SimpleUploadedFile("risks.csv", csv_content, content_type="text/csv")
        res1 = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': file1},
            format='multipart'
        )
        assert res1.status_code == status.HTTP_201_CREATED
        first_job_id = res1.data['id']

        # Second upload of same file content creates a distinct new job
        file2 = SimpleUploadedFile("risks.csv", csv_content, content_type="text/csv")
        res2 = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': file2},
            format='multipart'
        )
        assert res2.status_code == status.HTTP_201_CREATED
        assert res2.data['id'] != first_job_id

        # Verify 2 distinct jobs exist in database
        assert CSVImportJob.objects.filter(project=project).count() == 2

    def test_consultant_upload_to_inaccessible_project_returns_404(self, api_client, seeded_data):
        # Create unassigned organisation and project
        inaccessible_org = Organisation.objects.create(name='Secret Org', slug='secret-org')
        inaccessible_project = Project.objects.create(
            organisation=inaccessible_org,
            name='Secret Project',
            risk_score=0
        )

        consultant_client = api_client
        consultant_client.force_authenticate(user=seeded_data['consultant'])

        csv_file = SimpleUploadedFile("risks.csv", b"title,severity\nRisk,low\n", content_type="text/csv")
        response = consultant_client.post(
            f"/api/projects/{inaccessible_project.id}/csv-jobs/",
            {'file': csv_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_non_csv_file_rejected(self, consultant_client, seeded_data):
        project = seeded_data['project_acme']
        txt_file = SimpleUploadedFile("risks.txt", b"some plain text data", content_type="text/plain")

        response = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': txt_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'file' in response.data

    def test_upload_empty_csv_file_rejected(self, consultant_client, seeded_data):
        project = seeded_data['project_acme']
        empty_file = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")

        response = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': empty_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'file' in response.data


@pytest.mark.django_db
class TestCSVJobStatusEndpoints:
    def test_unauthenticated_get_job_rejected(self, api_client, seeded_data):
        job = CSVImportJob.objects.create(
            project=seeded_data['project_acme'],
            created_by=seeded_data['consultant'],
            filename='test.csv',
            status=JobStatus.QUEUED
        )
        response = api_client.get(f"/api/csv-jobs/{job.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_client_viewer_cannot_view_job_status(self, viewer_acme_client, seeded_data):
        job = CSVImportJob.objects.create(
            project=seeded_data['project_acme'],
            created_by=seeded_data['consultant'],
            filename='test.csv',
            status=JobStatus.QUEUED
        )
        response = viewer_acme_client.get(f"/api/csv-jobs/{job.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_consultant_get_own_job_status_success(self, consultant_client, seeded_data):
        job = CSVImportJob.objects.create(
            project=seeded_data['project_acme'],
            created_by=seeded_data['consultant'],
            filename='q4_risks.csv',
            status=JobStatus.PROCESSING,
            total_rows=25,
            processed_rows=10,
            error_details={'warnings': ['Row 3 has empty owner']}
        )

        response = consultant_client.get(f"/api/csv-jobs/{job.id}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['id'] == str(job.id)
        assert data['status'] == JobStatus.PROCESSING
        assert data['filename'] == 'q4_risks.csv'
        assert data['total_rows'] == 25
        assert data['processed_rows'] == 10
        assert data['error_details'] == {'warnings': ['Row 3 has empty owner']}

    def test_consultant_cannot_view_cross_tenant_job(self, api_client, seeded_data):
        # Create a foreign organisation, project, and consultant
        foreign_org = Organisation.objects.create(name='Foreign Org', slug='foreign-org')
        foreign_project = Project.objects.create(
            organisation=foreign_org,
            name='Foreign Project',
            risk_score=0
        )
        other_consultant = User.objects.create_user(
            email='other.consultant@example.com',
            name='Other Consultant',
            role=UserRole.CONSULTANT,
            password='Password123!'
        )
        ConsultantOrganisationAccess.objects.create(user=other_consultant, organisation=foreign_org)

        foreign_job = CSVImportJob.objects.create(
            project=foreign_project,
            created_by=other_consultant,
            filename='secret.csv',
            status=JobStatus.QUEUED
        )

        # Authenticate as Alice Consultant (who has no access to Foreign Org)
        consultant_client = api_client
        consultant_client.force_authenticate(user=seeded_data['consultant'])

        response = consultant_client.get(f"/api/csv-jobs/{foreign_job.id}/")
        # Returns 404 per multi-tenant isolation rules
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_job_returns_404(self, consultant_client):
        random_uuid = uuid.uuid4()
        response = consultant_client.get(f"/api/csv-jobs/{random_uuid}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

