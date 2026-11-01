from django.urls import path
from apps.users.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CurrentUserView,
    WebSocketTicketView,
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth_refresh'),
    path('me/', CurrentUserView.as_view(), name='auth_me'),
    path('ws-ticket/', WebSocketTicketView.as_view(), name='auth_ws_ticket'),
]

