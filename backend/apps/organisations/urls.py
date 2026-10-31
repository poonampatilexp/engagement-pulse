from django.urls import path
from apps.organisations.views import OrganisationListView, OrganisationDetailView

urlpatterns = [
    path('', OrganisationListView.as_view(), name='organisation_list'),
    path('<int:pk>/', OrganisationDetailView.as_view(), name='organisation_detail'),
]

