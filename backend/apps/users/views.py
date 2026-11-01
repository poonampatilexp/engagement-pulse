from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.users.serializers import CustomTokenObtainPairSerializer, UserSerializer
from apps.users.services import WebSocketTicketService


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Accepts email and password; returns access, refresh tokens and user profile.
    """
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh/
    Accepts refresh token; returns fresh access token.
    """
    pass


class CurrentUserView(APIView):
    """
    GET /api/auth/me/
    Returns the currently authenticated user's profile and organisation scope.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class WebSocketTicketView(APIView):
    """
    POST /api/auth/ws-ticket/
    Generates a single-use, short-lived ticket (30s) for authenticating WebSocket connections
    without exposing JWTs in URL query parameters.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticket = WebSocketTicketService.create_ticket(request.user)
        return Response(
            {
                'ticket': ticket,
                'expires_in': WebSocketTicketService.TICKET_TTL,
            },
            status=status.HTTP_201_CREATED
        )

