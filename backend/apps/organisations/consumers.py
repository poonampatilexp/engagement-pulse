from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.users.models import User
from apps.users.services import WebSocketTicketService
from apps.organisations.services import OrganisationService


class OrganisationUpdatesConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: /ws/organisations/<organisation_id>/updates/
    Subscribes authenticated users to real-time organisation risk and project updates.
    Enforces organisation multi-tenant isolation before accepting connection.
    Authenticates strictly via short-lived, single-use connection ticket (?ticket=...).
    """

    async def connect(self):
        # 1. Authenticate user using single-use connection ticket
        self.user = await self._authenticate_user()
        if not self.user or not self.user.is_authenticated:
            # 4401: Unauthorized
            await self.close(code=4401)
            return

        # 2. Extract organisation_id from URL route kwargs
        try:
            self.organisation_id = int(self.scope['url_route']['kwargs']['organisation_id'])
        except (KeyError, ValueError, TypeError):
            # 4400: Bad Request
            await self.close(code=4400)
            return

        # 3. Verify that user has access to requested organisation
        has_access = await self._check_organisation_access(self.user, self.organisation_id)
        if not has_access:
            # 4403: Forbidden - tenant isolation enforcement
            await self.close(code=4403)
            return

        # 4. Add connection to organisation-specific channel group
        self.group_name = f"org_{self.organisation_id}"
        if self.channel_layer:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

        # 5. Accept WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name') and self.channel_layer:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    @database_sync_to_async
    def _check_organisation_access(self, user: User, organisation_id: int) -> bool:
        return OrganisationService.user_has_organisation_access(user, organisation_id)

    async def _authenticate_user(self) -> User:
        """
        Authenticates connection using a short-lived single-use connection ticket.
        No long-lived JWTs or credentials are transmitted via URL query parameters.
        """
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        if not query_string:
            return AnonymousUser()

        params = parse_qs(query_string)
        tickets = params.get('ticket')
        if not tickets or not tickets[0]:
            return AnonymousUser()

        # Atomically consumes single-use ticket via Redis GETDEL
        user_id = await database_sync_to_async(WebSocketTicketService.consume_ticket)(tickets[0])
        if not user_id:
            return AnonymousUser()

        return await self._get_user_by_id(user_id)

    @database_sync_to_async
    def _get_user_by_id(self, user_id: int) -> User:
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return AnonymousUser()
