import logging
from typing import Optional
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import QuerySet
from apps.organisations.models import Organisation
from apps.users.models import User, UserRole

logger = logging.getLogger(__name__)


class OrganisationService:
    @staticmethod
    def get_organisations_for_user(user: User) -> QuerySet[Organisation]:
        """
        Returns the queryset of organisations accessible to the given user.
        - Client Viewers: Only their single assigned organisation.
        - Consultants: All organisations linked via ConsultantOrganisationAccess.
        - Anonymous / Unauthenticated: Empty queryset.
        """
        if not user or not user.is_authenticated:
            return Organisation.objects.none()

        if user.role == UserRole.CLIENT_VIEWER:
            if user.organisation_id:
                return Organisation.objects.filter(id=user.organisation_id)
            return Organisation.objects.none()

        if user.role == UserRole.CONSULTANT:
            return Organisation.objects.filter(consultant_access__user=user).distinct()

        return Organisation.objects.none()

    @staticmethod
    def get_organisation_for_user(user: User, organisation_id: int) -> Optional[Organisation]:
        """
        Retrieves a single organisation if the user is authorised to access it.
        Returns None if inaccessible or not found.
        """
        try:
            return OrganisationService.get_organisations_for_user(user).get(id=organisation_id)
        except Organisation.DoesNotExist:
            return None

    @staticmethod
    def user_has_organisation_access(user: User, organisation_id: int) -> bool:
        """
        Checks if the user has access to the given organisation.
        """
        if not user or not user.is_authenticated or not organisation_id:
            return False
        return OrganisationService.get_organisations_for_user(user).filter(id=organisation_id).exists()


class RealtimeBroadcastService:
    @staticmethod
    def broadcast_data_changed(organisation_id: int, project_id: Optional[int] = None) -> None:
        """
        Publishes a {"type": "data_changed"} invalidation signal to the affected organisation's
        Django Channels group (org_<organisation_id>).
        Transmits only invalidation signals (no risk details or sensitive data).
        """
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        group_name = f"org_{organisation_id}"
        message = {
            "type": "data_changed",
            "organisation_id": organisation_id,
        }
        if project_id is not None:
            message["project_id"] = project_id

        try:
            async_to_sync(channel_layer.group_send)(group_name, message)
        except Exception as exc:
            logger.warning("Failed to broadcast realtime update to %s: %s", group_name, exc)



