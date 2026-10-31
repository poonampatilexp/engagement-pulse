from typing import Optional
from django.db.models import QuerySet
from apps.organisations.models import Organisation
from apps.users.models import User, UserRole


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

