import pytest
from django.urls import reverse
from rest_framework import status
from apps.users.models import UserRole


@pytest.mark.django_db
class TestAuthentication:

    def test_login_consultant_success(self, api_client, seeded_data):
        url = reverse('auth_login')
        payload = {
            'email': 'consultant@engagementpulse.com',
            'password': 'Password123!'
        }
        response = api_client.post(url, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert 'access' in data
        assert 'refresh' in data
        assert 'user' in data
        assert data['user']['email'] == 'consultant@engagementpulse.com'
        assert data['user']['role'] == UserRole.CONSULTANT
        assert len(data['user']['organisations']) == 2
        org_slugs = {org['slug'] for org in data['user']['organisations']}
        assert org_slugs == {'acme-corp', 'globex-corp'}
        assert data['user']['organisation'] is None

    def test_login_client_viewer_success(self, api_client, seeded_data):
        url = reverse('auth_login')
        payload = {
            'email': 'viewer.acme@example.com',
            'password': 'Password123!'
        }
        response = api_client.post(url, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert 'access' in data
        assert 'refresh' in data
        assert 'user' in data
        assert data['user']['email'] == 'viewer.acme@example.com'
        assert data['user']['role'] == UserRole.CLIENT_VIEWER
        assert data['user']['organisation']['slug'] == 'acme-corp'
        assert data['user']['organisations'] is None

    def test_login_invalid_password(self, api_client, seeded_data):
        url = reverse('auth_login')
        payload = {
            'email': 'consultant@engagementpulse.com',
            'password': 'WrongPassword999!'
        }
        response = api_client.post(url, payload, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client, seeded_data):
        url = reverse('auth_login')
        payload = {
            'email': 'nobody@example.com',
            'password': 'Password123!'
        }
        response = api_client.post(url, payload, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, api_client, seeded_data):
        login_url = reverse('auth_login')
        login_payload = {
            'email': 'consultant@engagementpulse.com',
            'password': 'Password123!'
        }
        login_res = api_client.post(login_url, login_payload, format='json')
        refresh_token = login_res.data['refresh']

        refresh_url = reverse('auth_refresh')
        refresh_res = api_client.post(refresh_url, {'refresh': refresh_token}, format='json')

        assert refresh_res.status_code == status.HTTP_200_OK
        assert 'access' in refresh_res.data

    def test_auth_me_unauthenticated(self, api_client):
        url = reverse('auth_me')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_auth_me_consultant(self, consultant_client, seeded_data):
        url = reverse('auth_me')
        response = consultant_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['email'] == 'consultant@engagementpulse.com'
        assert data['role'] == UserRole.CONSULTANT
        assert len(data['organisations']) == 2
        assert data['organisation'] is None

    def test_auth_me_client_viewer(self, viewer_acme_client, seeded_data):
        url = reverse('auth_me')
        response = viewer_acme_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['email'] == 'viewer.acme@example.com'
        assert data['role'] == UserRole.CLIENT_VIEWER
        assert data['organisation']['slug'] == 'acme-corp'
        assert data['organisations'] is None

    def test_jwt_bearer_token_header_flow(self, api_client, seeded_data):
        # 1. Obtain token via login
        login_res = api_client.post(
            reverse('auth_login'),
            {'email': 'viewer.globex@example.com', 'password': 'Password123!'},
            format='json'
        )
        access_token = login_res.data['access']

        # 2. Access protected endpoint with Bearer header
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_res = api_client.get(reverse('auth_me'))

        assert me_res.status_code == status.HTTP_200_OK
        assert me_res.data['email'] == 'viewer.globex@example.com'
        assert me_res.data['organisation']['slug'] == 'globex-corp'

