import pytest
from rest_framework.test import APIClient
from apps.organisations.models import Organisation, ConsultantOrganisationAccess
from apps.users.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seeded_data(db):
    # Create Organisations
    org_acme = Organisation.objects.create(name='Acme Corp', slug='acme-corp')
    org_globex = Organisation.objects.create(name='Globex Corporation', slug='globex-corp')

    # Create Consultant assigned to both
    consultant = User.objects.create_user(
        email='consultant@engagementpulse.com',
        name='Alice Consultant',
        role=UserRole.CONSULTANT,
        password='Password123!'
    )
    ConsultantOrganisationAccess.objects.create(user=consultant, organisation=org_acme)
    ConsultantOrganisationAccess.objects.create(user=consultant, organisation=org_globex)

    # Create Client Viewer for Acme
    viewer_acme = User.objects.create_user(
        email='viewer.acme@example.com',
        name='Bob Acme Viewer',
        role=UserRole.CLIENT_VIEWER,
        organisation=org_acme,
        password='Password123!'
    )

    # Create Client Viewer for Globex
    viewer_globex = User.objects.create_user(
        email='viewer.globex@example.com',
        name='Carol Globex Viewer',
        role=UserRole.CLIENT_VIEWER,
        organisation=org_globex,
        password='Password123!'
    )

    return {
        'org_acme': org_acme,
        'org_globex': org_globex,
        'consultant': consultant,
        'viewer_acme': viewer_acme,
        'viewer_globex': viewer_globex,
    }


@pytest.fixture
def consultant_client(api_client, seeded_data):
    api_client.force_authenticate(user=seeded_data['consultant'])
    return api_client


@pytest.fixture
def viewer_acme_client(api_client, seeded_data):
    api_client.force_authenticate(user=seeded_data['viewer_acme'])
    return api_client


@pytest.fixture
def viewer_globex_client(api_client, seeded_data):
    api_client.force_authenticate(user=seeded_data['viewer_globex'])
    return api_client

