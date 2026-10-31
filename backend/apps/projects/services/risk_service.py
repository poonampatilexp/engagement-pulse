from typing import Optional, Dict, Any
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from apps.organisations.services import OrganisationService
from apps.projects.models import Project, Risk
from apps.projects.services.scoring_service import RiskScoringService
from apps.projects.services.project_service import ProjectService
from apps.users.models import User


class RiskService:
    @staticmethod
    def get_risks_for_project(user: User, project_id: int) -> Optional[QuerySet[Risk]]:
        """
        Returns queryset of risks for a project if accessible to user,
        otherwise None (to signal 404).
        """
        project = ProjectService.get_project_for_user(user, project_id)
        if not project:
            return None

        return Risk.objects.filter(project_id=project_id).select_related('project')

    @staticmethod
    def get_risk_for_user(user: User, risk_id: int) -> Optional[Risk]:
        """
        Retrieves a single risk if accessible to user, otherwise None (to signal 404).
        """
        if not user or not user.is_authenticated:
            return None

        try:
            risk = Risk.objects.select_related('project', 'project__organisation').get(id=risk_id)
        except Risk.DoesNotExist:
            return None

        # Verify tenant access
        if not OrganisationService.user_has_organisation_access(user, risk.project.organisation_id):
            return None

        return risk

    @staticmethod
    def create_risk(user: User, project_id: int, **data: Any) -> Risk:
        """
        Creates a new risk on a project and recalculates the project risk score.
        Only consultants can create risks.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can add risks to projects.")

        project = ProjectService.get_project_for_user(user, project_id)
        if not project:
            raise Project.DoesNotExist("Project not found or access denied.")

        with transaction.atomic():
            # Acquire Project row lock BEFORE risk creation
            project = Project.objects.select_for_update().get(id=project_id)
            risk = Risk.objects.create(
                project=project,
                title=data.get('title', '').strip(),
                description=data.get('description', '').strip(),
                severity=data.get('severity', 'medium'),
                status=data.get('status', 'open'),
                owner=data.get('owner', '').strip()
            )
            # Concurrency-safe automatic risk score recalculation on locked project
            RiskScoringService.recalculate_project_score(project.id, project=project)
            return risk

    @staticmethod
    def update_risk(user: User, risk_id: int, **data: Any) -> Risk:
        """
        Updates a risk's fields and recalculates the project risk score.
        Only consultants can update risks.
        Changing a risk's project is disallowed.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can update risks.")

        risk = RiskService.get_risk_for_user(user, risk_id)
        if not risk:
            raise Risk.DoesNotExist("Risk not found or access denied.")

        with transaction.atomic():
            # Acquire Project row lock BEFORE risk update
            project = Project.objects.select_for_update().get(id=risk.project_id)

            if 'title' in data and data['title'] is not None:
                risk.title = str(data['title']).strip()
            if 'description' in data and data['description'] is not None:
                risk.description = str(data['description']).strip()
            if 'severity' in data and data['severity'] is not None:
                risk.severity = data['severity']
            if 'status' in data and data['status'] is not None:
                risk.status = data['status']
            if 'owner' in data and data['owner'] is not None:
                risk.owner = str(data['owner']).strip()

            risk.save()
            # Concurrency-safe automatic risk score recalculation on locked project
            RiskScoringService.recalculate_project_score(project.id, project=project)
            return risk

    @staticmethod
    def delete_risk(user: User, risk_id: int) -> None:
        """
        Deletes a risk and recalculates the project risk score.
        Only consultants can delete risks.
        """
        if not user.is_consultant:
            raise PermissionDenied("Only consultants can delete risks.")

        risk = RiskService.get_risk_for_user(user, risk_id)
        if not risk:
            raise Risk.DoesNotExist("Risk not found or access denied.")

        with transaction.atomic():
            project_id = risk.project_id
            # Acquire Project row lock BEFORE risk deletion
            project = Project.objects.select_for_update().get(id=project_id)
            risk.delete()
            # Concurrency-safe automatic risk score recalculation on locked project
            RiskScoringService.recalculate_project_score(project_id, project=project)

