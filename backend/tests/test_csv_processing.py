import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from apps.projects.models import Project, Risk, CSVImportJob, JobStatus, RiskSeverity, RiskStatus
from apps.projects.services.csv_job_service import CSVImportJobService
from apps.projects.tasks import process_csv_import_task


@pytest.mark.django_db
class TestCSVBackgroundProcessing:
    def test_successful_csv_processing(self, seeded_data):
        project = seeded_data['project_acme']
        initial_score = project.risk_score
        assert initial_score == 0

        # CSV with 3 valid risks:
        # 1. Critical + Open = 4 * 3 = 12
        # 2. High + Mitigating = 3 * 2 = 6
        # 3. Low + Closed = 1 * 0 = 0
        # Expected project risk score = 18
        csv_content = (
            b"title,description,severity,status,owner\n"
            b"Critical API Failure,Server unresponsive,critical,open,Ops Team\n"
            b"Memory Leak,Increasing heap usage,high,mitigating,Backend Team\n"
            b"UI Typo,Minor cosmetic typo,low,closed,Frontend Team\n"
        )
        csv_file = SimpleUploadedFile("valid_risks.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )
        assert job.status == JobStatus.QUEUED

        # Process the job
        processed_job = CSVImportJobService.process_job(job.id)

        assert processed_job.status == JobStatus.COMPLETED
        assert processed_job.total_rows == 3
        assert processed_job.processed_rows == 3
        assert processed_job.error_details == {}

        # Verify risks were created in DB
        risks = Risk.objects.filter(project=project)
        assert risks.count() == 3
        titles = set(risks.values_list('title', flat=True))
        assert titles == {"Critical API Failure", "Memory Leak", "UI Typo"}

        # Verify project risk score was recalculated: 12 + 6 + 0 = 18
        project.refresh_from_db()
        assert project.risk_score == 18

    def test_invalid_csv_missing_title_column_fails(self, seeded_data):
        project = seeded_data['project_acme']
        csv_content = (
            b"description,severity,status,owner\n"
            b"Missing title column,high,open,Dev Team\n"
        )
        csv_file = SimpleUploadedFile("missing_title.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        processed_job = CSVImportJobService.process_job(job.id)

        assert processed_job.status == JobStatus.FAILED
        assert processed_job.processed_rows == 0
        assert "Missing required column: 'title'." in processed_job.error_details.get('errors', [])

        # Ensure no risks created and score untouched
        assert Risk.objects.filter(project=project).count() == 0
        project.refresh_from_db()
        assert project.risk_score == 0

    def test_invalid_csv_field_values_and_no_partial_imports(self, seeded_data):
        project = seeded_data['project_acme']

        # Row 2: Valid
        # Row 3: Invalid severity 'extreme'
        # Row 4: Empty title
        # Row 5: Invalid status 'pending'
        csv_content = (
            b"title,description,severity,status,owner\n"
            b"Valid Risk One,Good desc,medium,open,Alice\n"
            b"Invalid Severity,Some desc,extreme,open,Bob\n"
            b"  ,Empty title desc,low,open,Charlie\n"
            b"Invalid Status,Another desc,low,pending,David\n"
        )
        csv_file = SimpleUploadedFile("invalid_rows.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        processed_job = CSVImportJobService.process_job(job.id)

        assert processed_job.status == JobStatus.FAILED
        assert processed_job.total_rows == 4
        assert processed_job.processed_rows == 0

        errors = processed_job.error_details.get('errors', [])
        assert len(errors) == 3
        assert any("Row 3: Invalid severity 'extreme'" in err for err in errors)
        assert any("Row 4: 'title' is required and cannot be empty" in err for err in errors)
        assert any("Row 5: Invalid status 'pending'" in err for err in errors)

        # Verify atomicity - Valid Risk One was NOT imported
        assert Risk.objects.filter(project=project).count() == 0
        project.refresh_from_db()
        assert project.risk_score == 0

    def test_empty_csv_data_rows_fails(self, seeded_data):
        project = seeded_data['project_acme']
        csv_content = b"title,description,severity,status,owner\n"
        csv_file = SimpleUploadedFile("empty_data.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        processed_job = CSVImportJobService.process_job(job.id)

        assert processed_job.status == JobStatus.FAILED
        assert processed_job.processed_rows == 0
        assert "CSV file contains no data rows." in processed_job.error_details.get('errors', [])
        assert Risk.objects.filter(project=project).count() == 0

    def test_concurrent_claim_prevents_duplicate_processing(self, seeded_data):
        project = seeded_data['project_acme']
        csv_content = (
            b"title,severity,status\n"
            b"Concurrent Risk 1,high,open\n"
            b"Concurrent Risk 2,low,mitigating\n"
        )
        csv_file = SimpleUploadedFile("concurrent.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        # First worker claims and processes
        first_result = CSVImportJobService.process_job(job.id)
        assert first_result.status == JobStatus.COMPLETED
        assert Risk.objects.filter(project=project).count() == 2

        # Second worker attempts to process the same job (simulating concurrent delivery)
        second_result = CSVImportJobService.process_job(job.id)
        assert second_result.status == JobStatus.COMPLETED

        # Ensure no duplicate risks created
        assert Risk.objects.filter(project=project).count() == 2

    def test_already_processing_job_cannot_be_claimed(self, seeded_data):
        project = seeded_data['project_acme']
        csv_file = SimpleUploadedFile("dummy.csv", b"title\nRisk 1\n", content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        # Set job status to PROCESSING (simulating an active claim by Worker 1)
        job.status = JobStatus.PROCESSING
        job.save(update_fields=['status'])

        # Worker 2 attempts to claim
        result = CSVImportJobService.process_job(job.id)

        # Worker 2 could not claim, returns job without modifying status or creating risks
        assert result.status == JobStatus.PROCESSING
        assert Risk.objects.filter(project=project).count() == 0

    def test_exception_handler_does_not_override_completed_status(self, seeded_data):
        project = seeded_data['project_acme']
        csv_file = SimpleUploadedFile("dummy.csv", b"title\nRisk 1\n", content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        # Manually set to COMPLETED
        job.status = JobStatus.COMPLETED
        job.save(update_fields=['status'])

        # Attempt to process already-completed job
        result = CSVImportJobService.process_job(job.id)
        assert result.status == JobStatus.COMPLETED

    def test_unexpected_runtime_exception_marks_job_failed(self, seeded_data):
        project = seeded_data['project_acme']
        csv_file = SimpleUploadedFile("fail.csv", b"title\nRisk 1\n", content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        # Simulate unexpected exception during CSV parsing
        with patch.object(CSVImportJobService, '_parse_and_validate_csv', side_effect=RuntimeError("Disk read error")):
            result = CSVImportJobService.process_job(job.id)

        assert result.status == JobStatus.FAILED
        assert result.processed_rows == 0
        assert "Disk read error" in result.error_details.get('errors', [])
        assert Risk.objects.filter(project=project).count() == 0

    def test_dramatiq_actor_processes_job(self, seeded_data):
        project = seeded_data['project_acme']
        csv_content = (
            b"title,severity,status\n"
            b"Actor Processed Risk,medium,open\n"
        )
        csv_file = SimpleUploadedFile("actor_direct.csv", csv_content, content_type="text/csv")

        job = CSVImportJobService.create_import_job(
            user=seeded_data['consultant'],
            project=project,
            uploaded_file=csv_file
        )

        # Call the actor directly
        process_csv_import_task(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.processed_rows == 1
        assert Risk.objects.filter(project=project, title="Actor Processed Risk").exists()

    def test_end_to_end_upload_and_status_retrieval(self, consultant_client, seeded_data):
        project = seeded_data['project_acme']
        csv_content = (
            b"title,description,severity,status\n"
            b"E2E Risk 1,Description 1,medium,open\n"
            b"E2E Risk 2,Description 2,low,mitigating\n"
        )
        csv_file = SimpleUploadedFile("e2e_risks.csv", csv_content, content_type="text/csv")

        # Upload via API
        response = consultant_client.post(
            f"/api/projects/{project.id}/csv-jobs/",
            {'file': csv_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_201_CREATED
        job_id = response.data['id']
        assert response.data['status'] == JobStatus.QUEUED

        # Process job as background worker does
        CSVImportJobService.process_job(job_id)

        # Check job status via GET /api/csv-jobs/<job_id>/
        status_res = consultant_client.get(f"/api/csv-jobs/{job_id}/")
        assert status_res.status_code == status.HTTP_200_OK
        data = status_res.data
        assert data['status'] == JobStatus.COMPLETED
        assert data['total_rows'] == 2
        assert data['processed_rows'] == 2
        assert data['error_details'] == {}
