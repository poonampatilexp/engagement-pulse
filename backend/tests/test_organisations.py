import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from apps.organisations.models import Organisation, ConsultantOrganisationAccess
from apps.users.models import User, UserRole


@pytest.mark.django_db
class TestOrganisationAccess:

    def test_organisations_unauthenticated(self, api_client):
        url = reverse('organisation_list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_consultant_sees_assigned_organisations(self, consultant_client, seeded_data):
        url = reverse('organisation_list')
        response = consultant_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) == 2
        returned_slugs = {item['slug'] for item in data}
        assert returned_slugs == {'acme-corp', 'globex-corp'}

    def test_consultant_tenant_isolation(self, consultant_client, seeded_data):
        # Create a third organisation that the consultant is NOT assigned to
        unassigned_org = Organisation.objects.create(name='Initech Corp', slug='initech-corp')

        # 1. Consultant should NOT see Initech in the list
        list_res = consultant_client.get(reverse('organisation_list'))
        assert list_res.status_code == status.HTTP_200_OK
        returned_ids = [item['id'] for item in list_res.data]
        assert unassigned_org.id not in returned_ids

        # 2. Consultant requesting detail for unassigned org should receive 404
        detail_res = consultant_client.get(reverse('organisation_detail', kwargs={'pk': unassigned_org.id}))
        assert detail_res.status_code == status.HTTP_404_NOT_FOUND

    def test_client_viewer_sees_only_own_organisation(self, viewer_acme_client, seeded_data):
        url = reverse('organisation_list')
        response = viewer_acme_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) == 1
        assert data[0]['slug'] == 'acme-corp'

    def test_cross_organisation_access_denied_for_client_viewer(self, viewer_acme_client, seeded_data):
        # Acme viewer trying to view Globex organisation detail
        globex_id = seeded_data['org_globex'].id
        url = reverse('organisation_detail', kwargs={'pk': globex_id})
        response = viewer_acme_client.get(url)

        # Per AGENTS.md: Return 404 for inaccessible tenant resources
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_client_viewer_can_access_own_organisation_detail(self, viewer_acme_client, seeded_data):
        acme_id = seeded_data['org_acme'].id
        url = reverse('organisation_detail', kwargs={'pk': acme_id})
        response = viewer_acme_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['slug'] == 'acme-corp'

    def test_consultant_can_access_assigned_organisation_detail(self, consultant_client, seeded_data):
        for org in [seeded_data['org_acme'], seeded_data['org_globex']]:
            url = reverse('organisation_detail', kwargs={'pk': org.id})
            response = consultant_client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['slug'] == org.slug


@pytest.mark.django_db
class TestDatabaseConstraintsAndValidation:

    def test_unique_consultant_organisation_assignment_db_constraint(self, seeded_data):
        """Enforces unique consultant/organisation assignments at the database level."""
        with pytest.raises(IntegrityError):
            ConsultantOrganisationAccess.objects.create(
                user=seeded_data['consultant'],
                organisation=seeded_data['org_acme']
            )

    def test_client_viewer_requires_organisation(self):
        """Validates that a client viewer must belong to an organisation."""
        user = User(
            email='noviewer@example.com',
            name='No Viewer',
            role=UserRole.CLIENT_VIEWER,
            organisation=None
        )
        with pytest.raises(ValidationError):
            user.clean()

    def test_consultant_disallows_direct_organisation(self, seeded_data):
        """Validates that a consultant cannot be assigned directly to an organisation on User model."""
        user = User(
            email='badconsultant@example.com',
            name='Bad Consultant',
            role=UserRole.CONSULTANT,
            organisation=seeded_data['org_acme']
        )
        with pytest.raises(ValidationError):
            user.clean()


@pytest.mark.django_db
class TestSeedDataCommand:

    def test_seed_data_is_repeatable(self):
        """Executes seed_data twice and verifies idempotency and data integrity."""
        call_command('seed_data')
        call_command('seed_data')

        assert Organisation.objects.count() >= 2
        consultant = User.objects.get(email='consultant@engagementpulse.com')
        assert consultant.role == UserRole.CONSULTANT
        assert consultant.consultant_access.count() == 2

        viewer_acme = User.objects.get(email='viewer.acme@example.com')
        assert viewer_acme.role == UserRole.CLIENT_VIEWER
        assert viewer_acme.organisation.slug == 'acme-corp'

        viewer_globex = User.objects.get(email='viewer.globex@example.com')
        assert viewer_globex.role == UserRole.CLIENT_VIEWER
        assert viewer_globex.organisation.slug == 'globex-corp'

