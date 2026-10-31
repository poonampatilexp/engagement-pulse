from django.urls import path
from apps.projects.views import (
    OrganisationProjectListCreateView,
    ProjectDetailView,
    ProjectRiskListCreateView,
    RiskDetailView,
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
]

