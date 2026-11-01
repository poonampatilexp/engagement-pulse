import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from channels.db import database_sync_to_async
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.organisations.models import Organisation
from apps.projects.models import Risk, CSVImportJob, JobStatus
from apps.projects.services.risk_service import RiskService
from apps.projects.services.csv_job_service import CSVImportJobService
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


@pytest.mark.django_db(transaction=True)
class TestLiveDashboardUpdates:
    def test_risk_creation_broadcasts_data_changed_to_organisation(self, seeded_data):
        viewer = seeded_data['viewer_acme']
        org_acme = seeded_data['org_acme']
        project_acme = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        ticket = WebSocketTicketService.create_ticket(viewer)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )

        async def _test():
            connected, _ = await communicator.connect()
            assert connected is True

            try:
                # Consultant creates risk within a committed transaction
                await database_sync_to_async(RiskService.create_risk)(
                    consultant,
                    project_acme.id,
                    title="Live Test Risk",
                    description="Confidential audit finding",
                    severity="high",
                    status="open",
                    owner="Auditor"
                )

                # Client Viewer receives invalidation signal
                msg = await communicator.receive_json_from(timeout=3)
                assert msg['type'] == 'data_changed'
                assert msg['organisation_id'] == org_acme.id
                assert msg['project_id'] == project_acme.id

                # Confirm NO sensitive data or risk details are leaked
                assert 'title' not in msg
                assert 'description' not in msg
                assert 'severity' not in msg
                assert 'score' not in msg
            finally:
                await communicator.disconnect()

        async_to_sync(_test)()

    def test_risk_update_broadcasts_data_changed_to_organisation(self, seeded_data):
        viewer = seeded_data['viewer_acme']
        org_acme = seeded_data['org_acme']
        project_acme = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        risk = RiskService.create_risk(
            consultant,
            project_acme.id,
            title="Initial Risk",
            severity="low",
            status="open"
        )

        ticket = WebSocketTicketService.create_ticket(viewer)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )

        async def _test():
            connected, _ = await communicator.connect()
            assert connected is True

            try:
                await database_sync_to_async(RiskService.update_risk)(
                    consultant,
                    risk.id,
                    severity="critical"
                )

                msg = await communicator.receive_json_from(timeout=3)
                assert msg['type'] == 'data_changed'
                assert msg['organisation_id'] == org_acme.id
                assert msg['project_id'] == project_acme.id
            finally:
                await communicator.disconnect()

        async_to_sync(_test)()

    def test_data_changed_isolated_to_correct_organisation(self, seeded_data):
        viewer_acme = seeded_data['viewer_acme']
        org_acme = seeded_data['org_acme']
        project_acme = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        viewer_globex = seeded_data['viewer_globex']
        org_globex = seeded_data['org_globex']

        ticket_acme = WebSocketTicketService.create_ticket(viewer_acme)
        ticket_globex = WebSocketTicketService.create_ticket(viewer_globex)

        c_acme = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket_acme}"
        )
        c_globex = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_globex.id}/updates/?ticket={ticket_globex}"
        )

        async def _test():
            connected_acme, _ = await c_acme.connect()
            connected_globex, _ = await c_globex.connect()
            assert connected_acme is True
            assert connected_globex is True

            try:
                # Consultant creates risk for Acme only
                await database_sync_to_async(RiskService.create_risk)(
                    consultant,
                    project_acme.id,
                    title="Acme-only risk",
                    severity="medium",
                    status="open"
                )

                # Acme viewer must receive the data_changed event
                msg_acme = await c_acme.receive_json_from(timeout=3)
                assert msg_acme['type'] == 'data_changed'
                assert msg_acme['organisation_id'] == org_acme.id

                # Globex viewer must receive NOTHING (strict tenant isolation)
                received_nothing = await c_globex.receive_nothing(timeout=0.5)
                assert received_nothing is True
            finally:
                await c_acme.disconnect()
                await c_globex.disconnect()

        async_to_sync(_test)()

    def test_csv_import_completion_broadcasts_data_changed(self, seeded_data):
        viewer = seeded_data['viewer_acme']
        org_acme = seeded_data['org_acme']
        project_acme = seeded_data['project_acme']
        consultant = seeded_data['consultant']

        ticket = WebSocketTicketService.create_ticket(viewer)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/organisations/{org_acme.id}/updates/?ticket={ticket}"
        )

        async def _test():
            connected, _ = await communicator.connect()
            assert connected is True

            try:
                csv_content = b"title,severity,status,owner,description\nImport Risk 1,high,open,Auditor,Test CSV"
                csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")

                job = await database_sync_to_async(CSVImportJob.objects.create)(
                    project=project_acme,
                    created_by=consultant,
                    file=csv_file,
                    filename="test.csv",
                    status=JobStatus.QUEUED,
                )

                # Process job which transitions to COMPLETED and commits
                await database_sync_to_async(CSVImportJobService.process_job)(job.id)

                # WebSocket client receives data_changed
                msg = await communicator.receive_json_from(timeout=3)
                assert msg['type'] == 'data_changed'
                assert msg['organisation_id'] == org_acme.id
                assert msg['project_id'] == project_acme.id
            finally:
                await communicator.disconnect()

        async_to_sync(_test)()

