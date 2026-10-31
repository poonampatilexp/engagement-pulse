from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.organisations.serializers import OrganisationSerializer
from apps.organisations.services import OrganisationService


class OrganisationListView(APIView):
    """
    GET /api/organisations/
    Returns list of organisations scoped to the authenticated user's permissions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organisations = OrganisationService.get_organisations_for_user(request.user)
        serializer = OrganisationSerializer(organisations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrganisationDetailView(APIView):
    """
    GET /api/organisations/<pk>/
    Returns single organisation if accessible to the user, otherwise 404.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        org = OrganisationService.get_organisation_for_user(request.user, pk)
        if not org:
            return Response(
                {'detail': 'Organisation not found or access denied.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = OrganisationSerializer(org)
        return Response(serializer.data, status=status.HTTP_200_OK)

