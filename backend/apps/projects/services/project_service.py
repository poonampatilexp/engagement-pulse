from typing import Optional
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from apps.organisations.models import Organisation
from apps.organisations.services import OrganisationService
from apps.projects.models import Project
from apps.users.models import User, UserRole


class ProjectService:
    @staticmethod
    def get_projects_for_user(user: User, organisation_id: int) -> Optional[QuerySet[Project]]:
        """
        Returns queryset of projects for an organisation if accessible to user,
        otherwise None (to signal 404).
        """
        if not user or not user.is_authenticated:
            return None

        # Check tenant access to organisation
        org = OrganisationService.get_organisation_for_user(user, organisation_id)
        if not org:
            return None

        return Project.objects.filter(organisation_id=organisation_id).select_related('organisation')

    @staticmethod
    def get_project_for_user(user: User, project_id: int) -> Optional[Project]:
        """
        Retrieves a single project if accessible to the user, otherwise None (signals 404).
        """
        if not user or not user.is_authenticated:
            return None

        try:
            project = Project.objects.select_related('organisation').get(id=project_id)
        except Project.DoesNotExist:
            return None

        # Verify user has access to the project's organisation
        if not OrganisationService.user_has_organisation_access(user, project.organisation_id):
            return None

        return project

    @staticmethod
    def create_project(user: User, organisation_id: int, name: str) -> Project:
        """
        Creates a new project within an organisation.
        Only consultants can create projects.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can create projects.")

        org = OrganisationService.get_organisation_for_user(user, organisation_id)
        if not org:
            raise Project.DoesNotExist("Organisation not found or access denied.")

        with transaction.atomic():
            project = Project.objects.create(
                organisation=org,
                name=name.strip(),
                risk_score=0
            )
            return project

    @staticmethod
    def update_project(user: User, project_id: int, **kwargs) -> Project:
        """
        Updates project attributes (e.g. name).
        Only consultants can update projects.
        Client-supplied risk_score or organisation alterations are disallowed.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can update projects.")

        project = ProjectService.get_project_for_user(user, project_id)
        if not project:
            raise Project.DoesNotExist("Project not found or access denied.")

        with transaction.atomic():
            if 'name' in kwargs and kwargs['name']:
                project.name = kwargs['name'].strip()
            project.save()
            return project

    @staticmethod
    def delete_project(user: User, project_id: int) -> None:
        """
        Deletes a project.
        Only consultants can delete projects.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can delete projects.")

        project = ProjectService.get_project_for_user(user, project_id)
        if not project:
            raise Project.DoesNotExist("Project not found or access denied.")

        with transaction.atomic():
            project.delete()

