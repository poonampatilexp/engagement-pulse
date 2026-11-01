import csv
import io
import uuid
from typing import Optional, List, Dict, Any, Tuple
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from apps.organisations.services import OrganisationService, RealtimeBroadcastService
from apps.projects.models import (
    Project,
    Risk,
    CSVImportJob,
    JobStatus,
    RiskSeverity,
    RiskStatus,
)
from apps.projects.services.project_service import ProjectService
from apps.projects.services.scoring_service import RiskScoringService
from apps.users.models import User


class CSVImportJobService:
    @staticmethod
    def create_import_job(
        user: User,
        project: Project,
        uploaded_file
    ) -> CSVImportJob:
        """
        Validates consultant permissions and creates a new queued CSV import job.
        Dispatches background processing task after database transaction commits.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can upload CSV imports.")

        # Verify tenant organisation access
        if not OrganisationService.user_has_organisation_access(user, project.organisation_id):
            raise Project.DoesNotExist("Project not found or access denied.")

        with transaction.atomic():
            job = CSVImportJob.objects.create(
                project=project,
                created_by=user,
                file=uploaded_file,
                filename=uploaded_file.name,
                status=JobStatus.QUEUED,
                error_details={},
            )
            # Enqueue Dramatiq worker task after successful database commit
            from apps.projects.tasks import process_csv_import_task
            transaction.on_commit(lambda: process_csv_import_task.send(str(job.id)))

        return job

    @classmethod
    def _parse_and_validate_csv(cls, file_field) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """
        Helper that reads the CSV file and validates columns and rows against Risk model rules.
        Returns: (valid_records, errors, total_rows_read)
        """
        errors: List[str] = []
        valid_records: List[Dict[str, Any]] = []
        total_rows = 0

        if not file_field:
            return [], ["No file attached to import job."], 0

        file_field.open('rb')
        try:
            stream = io.TextIOWrapper(file_field, encoding='utf-8-sig', errors='replace')
            reader = csv.DictReader(stream)

            if not reader.fieldnames:
                return [], ["CSV file contains no header or is empty."], 0

            # Normalize header names case-insensitively
            col_map = {name.strip().lower(): name for name in reader.fieldnames if name and name.strip()}
            if 'title' not in col_map:
                return [], ["Missing required column: 'title'."], 0

            for row_idx, row in enumerate(reader, start=2):
                total_rows += 1
                row_errors = []

                # Title: required, non-empty, max 255 chars
                raw_title = row.get(col_map.get('title'), '')
                title = raw_title.strip() if raw_title else ''
                if not title:
                    row_errors.append(f"Row {row_idx}: 'title' is required and cannot be empty.")
                elif len(title) > 255:
                    row_errors.append(f"Row {row_idx}: 'title' exceeds 255 characters.")

                # Severity: optional, defaults to 'medium', validates against RiskSeverity
                raw_sev = row.get(col_map.get('severity'), '')
                if raw_sev and raw_sev.strip():
                    sev = raw_sev.strip().lower()
                    if sev not in RiskSeverity.values:
                        choices = ', '.join(RiskSeverity.values)
                        row_errors.append(f"Row {row_idx}: Invalid severity '{raw_sev.strip()}'. Allowed choices: {choices}.")
                else:
                    sev = RiskSeverity.MEDIUM

                # Status: optional, defaults to 'open', validates against RiskStatus
                raw_stat = row.get(col_map.get('status'), '')
                if raw_stat and raw_stat.strip():
                    stat = raw_stat.strip().lower()
                    if stat not in RiskStatus.values:
                        choices = ', '.join(RiskStatus.values)
                        row_errors.append(f"Row {row_idx}: Invalid status '{raw_stat.strip()}'. Allowed choices: {choices}.")
                else:
                    stat = RiskStatus.OPEN

                # Description & Owner
                raw_desc = row.get(col_map.get('description'), '')
                desc = raw_desc.strip() if raw_desc else ''

                raw_owner = row.get(col_map.get('owner'), '')
                owner = raw_owner.strip() if raw_owner else ''
                if len(owner) > 255:
                    row_errors.append(f"Row {row_idx}: 'owner' exceeds 255 characters.")

                if row_errors:
                    errors.extend(row_errors)
                else:
                    valid_records.append({
                        'title': title,
                        'description': desc,
                        'severity': sev,
                        'status': stat,
                        'owner': owner,
                    })

            if total_rows == 0 and not errors:
                errors.append("CSV file contains no data rows.")

        finally:
            file_field.close()

        return valid_records, errors, total_rows

    @classmethod
    def process_job(cls, job_id: uuid.UUID | str) -> Optional[CSVImportJob]:
        """
        Orchestrates CSV import job processing with a PostgreSQL-backed atomic claim.
        Guarantees that concurrent workers cannot claim the same job simultaneously,
        and repeated deliveries cannot duplicate imported risks.
        """
        # Minimal PostgreSQL-backed atomic job claim: only claim if currently QUEUED
        claimed = CSVImportJob.objects.filter(
            id=job_id,
            status=JobStatus.QUEUED
        ).update(status=JobStatus.PROCESSING)

        if not claimed:
            # Job is already PROCESSING, COMPLETED, or FAILED by another worker
            return CSVImportJob.objects.filter(id=job_id).first()

        job = CSVImportJob.objects.select_related('project').get(id=job_id)

        try:
            valid_records, errors, total_rows = cls._parse_and_validate_csv(job.file)

            if errors:
                job.status = JobStatus.FAILED
                job.total_rows = total_rows
                job.processed_rows = 0
                job.error_details = {'errors': errors}
                job.save(update_fields=['status', 'total_rows', 'processed_rows', 'error_details', 'updated_at'])
                return job

            # Atomically create risks, recalculate score, and record completed status
            with transaction.atomic():
                risks = [
                    Risk(
                        project_id=job.project_id,
                        title=r['title'],
                        description=r['description'],
                        severity=r['severity'],
                        status=r['status'],
                        owner=r['owner'],
                    )
                    for r in valid_records
                ]
                Risk.objects.bulk_create(risks)
                RiskScoringService.recalculate_project_score(job.project_id)

                job.status = JobStatus.COMPLETED
                job.total_rows = len(valid_records)
                job.processed_rows = len(valid_records)
                job.error_details = {}
                job.save(update_fields=['status', 'total_rows', 'processed_rows', 'error_details', 'updated_at'])

                org_id = job.project.organisation_id
                proj_id = job.project_id
                transaction.on_commit(
                    lambda: RealtimeBroadcastService.broadcast_data_changed(org_id, project_id=proj_id)
                )

            return job

        except Exception as exc:
            # Safely handle unexpected failures without overriding already completed jobs
            try:
                job.refresh_from_db()
                if job.status == JobStatus.COMPLETED:
                    return job
                job.status = JobStatus.FAILED
                job.processed_rows = 0
                job.error_details = {'errors': [str(exc)]}
                job.save(update_fields=['status', 'processed_rows', 'error_details', 'updated_at'])
            except Exception:
                pass
            return job

    @staticmethod
    def get_job_for_user(user: User, job_id: uuid.UUID | str) -> Optional[CSVImportJob]:
        """
        Retrieves a CSV import job if accessible to the authenticated consultant.
        Enforces tenant organisation isolation and user job ownership.
        Returns None to signal 404.
        """
        if not user or not user.is_authenticated:
            return None

        if not user.is_consultant:
            raise PermissionDenied("Only consultants can view CSV import jobs.")

        try:
            job = CSVImportJob.objects.select_related(
                'project',
                'project__organisation',
                'created_by'
            ).get(id=job_id)
        except (CSVImportJob.DoesNotExist, ValueError):
            return None

        # Verify user has access to the project's organisation
        if not OrganisationService.user_has_organisation_access(user, job.project.organisation_id):
            return None

        # Enforce that only the creator/authorised consultant can view their job
        if job.created_by_id != user.id:
            return None

        return job

    @staticmethod
    def get_jobs_for_project(user: User, project_id: int) -> Optional[QuerySet[CSVImportJob]]:
        """
        Lists all CSV jobs created by the consultant for an accessible project.
        """
        if not user or not user.is_authenticated:
            return None

        if not user.is_consultant:
            raise PermissionDenied("Only consultants can view CSV import jobs.")

        project = ProjectService.get_project_for_user(user, project_id)
        if not project:
            return None

        return CSVImportJob.objects.filter(
            project=project,
            created_by=user
        ).select_related('project')
