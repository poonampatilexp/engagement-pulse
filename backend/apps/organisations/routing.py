from django.urls import re_path
from apps.organisations.consumers import OrganisationUpdatesConsumer

websocket_urlpatterns = [
    re_path(r'^ws/organisations/(?P<organisation_id>\d+)/updates/?$', OrganisationUpdatesConsumer.as_asgi()),
]

