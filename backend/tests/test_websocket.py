import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from apps.organisations.models import Organisation
from apps.users.services import WebSocketTicketService


def run_ws(communicator):
    """
    Executes WebSocket connect and clean disconnect in the same event loop.
    """
    async def _runner():
        connected, result = await communicator.connect()
        try:
            return connected, result
        finally:
            if connected:
                await communicator.disconnect()
    return async_to_sync(_runner)()


@pytest.mark.django_db(transaction=True)
class TestWebSocketConnection:
    def test_authenticated_consultant_can_connect_via_ticket(self, seeded_data):
        consultant = seeded_data['consultant']
        org_acme = seeded_data['org_acme']

        ticket = WebSocketTicketService.create_ticket(consultant)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )

        connected, _ = run_ws(communicator)
        assert connected is True

    def test_client_viewer_can_connect_to_own_organisation_via_ticket(self, seeded_data):
        viewer = seeded_data['viewer_acme']
        org_acme = seeded_data['org_acme']

        ticket = WebSocketTicketService.create_ticket(viewer)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )

        connected, _ = run_ws(communicator)
        assert connected is True

    def test_client_viewer_rejected_from_other_organisation(self, seeded_data):
        viewer = seeded_data['viewer_acme']
        org_globex = seeded_data['org_globex']

        ticket = WebSocketTicketService.create_ticket(viewer)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_globex.id}/updates/?ticket={ticket}"
        )

        connected, close_code = run_ws(communicator)
        assert connected is False
        assert close_code == 4403

    def test_consultant_rejected_from_unassigned_organisation(self, seeded_data):
        consultant = seeded_data['consultant']
        unassigned_org = Organisation.objects.create(name='Initech', slug='initech')

        ticket = WebSocketTicketService.create_ticket(consultant)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{unassigned_org.id}/updates/?ticket={ticket}"
        )

        connected, close_code = run_ws(communicator)
        assert connected is False
        assert close_code == 4403

    def test_unauthenticated_connection_without_ticket_rejected(self, seeded_data):
        org_acme = seeded_data['org_acme']

        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/"
        )

        connected, close_code = run_ws(communicator)
        assert connected is False
        assert close_code == 4401

    def test_invalid_or_nonexistent_ticket_rejected(self, seeded_data):
        org_acme = seeded_data['org_acme']

        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket=invalid-ticket-value"
        )

        connected, close_code = run_ws(communicator)
        assert connected is False
        assert close_code == 4401

    def test_ticket_is_single_use_via_getdel(self, seeded_data):
        consultant = seeded_data['consultant']
        org_acme = seeded_data['org_acme']

        ticket = WebSocketTicketService.create_ticket(consultant)

        # First connection consumes ticket successfully via GETDEL
        c1 = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )
        connected1, _ = run_ws(c1)
        assert connected1 is True

        # Second connection with same ticket must fail (already consumed and deleted)
        c2 = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )
        connected2, close_code2 = run_ws(c2)
        assert connected2 is False
        assert close_code2 == 4401

    def test_ws_ticket_api_authenticated(self, consultant_client):
        response = consultant_client.post('/api/auth/ws-ticket/')
        assert response.status_code == 201
        assert 'ticket' in response.data
        assert response.data['expires_in'] == 30

    def test_ws_ticket_api_unauthenticated(self, api_client):
        response = api_client.post('/api/auth/ws-ticket/')
        assert response.status_code == 401
