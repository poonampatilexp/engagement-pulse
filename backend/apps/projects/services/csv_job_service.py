import uuid
from typing import Optional
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from apps.organisations.services import OrganisationService
from apps.projects.models import Project, CSVImportJob, JobStatus
from apps.projects.services.project_service import ProjectService
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
        Every valid upload creates a new job.
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
