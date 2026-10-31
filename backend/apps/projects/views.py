from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import PermissionDenied
from apps.organisations.services import OrganisationService
from apps.projects.models import Project, Risk, CSVImportJob
from apps.projects.serializers import (
    ProjectSerializer,
    RiskSerializer,
    CSVImportJobSerializer,
    CSVUploadSerializer,
)
from apps.projects.services.project_service import ProjectService
from apps.projects.services.risk_service import RiskService
from apps.projects.services.csv_job_service import CSVImportJobService


class OrganisationProjectListCreateView(APIView):
    """
    GET  /api/organisations/<organisation_id>/projects/
    POST /api/organisations/<organisation_id>/projects/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, organisation_id: int):
        projects = ProjectService.get_projects_for_user(request.user, organisation_id)
        if projects is None:
            return Response(
                {'detail': 'Organisation not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, organisation_id: int):
        org = OrganisationService.get_organisation_for_user(request.user, organisation_id)
        if not org:
            return Response(
                {'detail': 'Organisation not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot create projects.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        project = ProjectService.create_project(
            user=request.user,
            organisation_id=organisation_id,
            name=serializer.validated_data['name']
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    """
    GET    /api/projects/<project_id>/
    PATCH  /api/projects/<project_id>/
    DELETE /api/projects/<project_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id: int):
        project = ProjectService.get_project_for_user(request.user, project_id)
        if not project:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    def patch(self, request, project_id: int):
        project = ProjectService.get_project_for_user(request.user, project_id)
        if not project:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot update projects.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_project = ProjectService.update_project(
            user=request.user,
            project_id=project_id,
            **serializer.validated_data
        )
        return Response(ProjectSerializer(updated_project).data, status=status.HTTP_200_OK)

    def delete(self, request, project_id: int):
        project = ProjectService.get_project_for_user(request.user, project_id)
        if not project:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot delete projects.'},
                status=status.HTTP_403_FORBIDDEN
            )

        ProjectService.delete_project(request.user, project_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectRiskListCreateView(APIView):
    """
    GET  /api/projects/<project_id>/risks/
    POST /api/projects/<project_id>/risks/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id: int):
        risks = RiskService.get_risks_for_project(request.user, project_id)
        if risks is None:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = RiskSerializer(risks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, project_id: int):
        project = ProjectService.get_project_for_user(request.user, project_id)
        if not project:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot add risks.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RiskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        risk = RiskService.create_risk(
            user=request.user,
            project_id=project_id,
            **serializer.validated_data
        )
        return Response(RiskSerializer(risk).data, status=status.HTTP_201_CREATED)


class RiskDetailView(APIView):
    """
    GET    /api/risks/<risk_id>/
    PATCH  /api/risks/<risk_id>/
    DELETE /api/risks/<risk_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, risk_id: int):
        risk = RiskService.get_risk_for_user(request.user, risk_id)
        if not risk:
            return Response(
                {'detail': 'Risk not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(RiskSerializer(risk).data, status=status.HTTP_200_OK)

    def patch(self, request, risk_id: int):
        risk = RiskService.get_risk_for_user(request.user, risk_id)
        if not risk:
            return Response(
                {'detail': 'Risk not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot update risks.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RiskSerializer(risk, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_risk = RiskService.update_risk(
            user=request.user,
            risk_id=risk_id,
            **serializer.validated_data
        )
        return Response(RiskSerializer(updated_risk).data, status=status.HTTP_200_OK)

    def delete(self, request, risk_id: int):
        risk = RiskService.get_risk_for_user(request.user, risk_id)
        if not risk:
            return Response(
                {'detail': 'Risk not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.is_consultant:
            return Response(
                {'detail': 'Client viewers have read-only access and cannot delete risks.'},
                status=status.HTTP_403_FORBIDDEN
            )

        RiskService.delete_risk(request.user, risk_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CSVUploadView(APIView):
    """
    POST /api/projects/<project_id>/csv-jobs/
    POST /api/projects/<project_id>/import-csv/
    Validates CSV file and creates a new queued import job.
    Only authorised consultants can upload CSV imports.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id: int):
        if not request.user.is_consultant:
            return Response(
                {'detail': 'Only consultants can upload CSV imports.'},
                status=status.HTTP_403_FORBIDDEN
            )

        project = ProjectService.get_project_for_user(request.user, project_id)
        if not project:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CSVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['file']

        job = CSVImportJobService.create_import_job(
            user=request.user,
            project=project,
            uploaded_file=uploaded_file
        )

        return Response(CSVImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class CSVJobDetailView(APIView):
    """
    GET /api/csv-jobs/<job_id>/
    Retrieves job status and error details for an authorised consultant.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        if not request.user.is_consultant:
            return Response(
                {'detail': 'Only consultants can view CSV import jobs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        job = CSVImportJobService.get_job_for_user(request.user, job_id)
        if not job:
            return Response(
                {'detail': 'CSV import job not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(CSVImportJobSerializer(job).data, status=status.HTTP_200_OK)


class ProjectCSVJobListView(APIView):
    """
    GET /api/projects/<project_id>/csv-jobs/
    Lists CSV import jobs for a project accessible to the consultant.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id: int):
        if not request.user.is_consultant:
            return Response(
                {'detail': 'Only consultants can view CSV import jobs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        jobs = CSVImportJobService.get_jobs_for_project(request.user, project_id)
        if jobs is None:
            return Response(
                {'detail': 'Project not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(CSVImportJobSerializer(jobs, many=True).data, status=status.HTTP_200_OK)


