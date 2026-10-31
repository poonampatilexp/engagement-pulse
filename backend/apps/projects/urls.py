from django.urls import path
from apps.projects.views import (
    OrganisationProjectListCreateView,
    ProjectDetailView,
    ProjectRiskListCreateView,
    RiskDetailView,
    CSVUploadView,
    CSVJobDetailView,
    ProjectCSVJobListView,
)

urlpatterns = [
    # Organisation-scoped projects
    path(
        'organisations/<int:organisation_id>/projects/',
        OrganisationProjectListCreateView.as_view(),
        name='organisation_project_list_create'
    ),
    # Project detail
    path(
        'projects/<int:project_id>/',
        ProjectDetailView.as_view(),
        name='project_detail'
    ),
    # Project-scoped risks
    path(
        'projects/<int:project_id>/risks/',
        ProjectRiskListCreateView.as_view(),
        name='project_risk_list_create'
    ),
    # Risk detail
    path(
        'risks/<int:risk_id>/',
        RiskDetailView.as_view(),
        name='risk_detail'
    ),
    # CSV Job upload and project-scoped job list
    path(
        'projects/<int:project_id>/csv-jobs/',
        CSVUploadView.as_view(),
        name='project_csv_upload'
    ),
    path(
        'projects/<int:project_id>/import-csv/',
        CSVUploadView.as_view(),
        name='project_import_csv'
    ),
    # CSV Job status and error details retrieval
    path(
        'csv-jobs/<uuid:job_id>/',
        CSVJobDetailView.as_view(),
        name='csv_job_detail'
    ),
]


