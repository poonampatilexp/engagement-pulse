import json
import logging
from typing import Optional
import uuid
import redis
from config import settings

logger = logging.getLogger(__name__)


class BroadcastService:
    REDIS_CHANNEL_PREFIX = "fastapi:org"

    @classmethod
    def _get_redis(cls) -> redis.Redis:
        return redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    @classmethod
    def broadcast_data_changed(
        cls,
        organisation_id: int,
        project_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Publishes a {"type": "data_changed"} event to Redis Pub/Sub for the

        specified organisation.

        All subscribed FastAPI instances receive this event and forward it to
        their locally connected WebSockets for that organisation.
        """
        event_id = str(uuid.uuid4())
        payload = {
            "type": "data_changed",
            "event_id": event_id,
            "organisation_id": organisation_id,
        }
        if project_id is not None:
            payload["project_id"] = project_id
        if reason:
            payload["reason"] = reason

        channel = f"{cls.REDIS_CHANNEL_PREFIX}:{organisation_id}"
        message_json = json.dumps(payload)

        try:
            r = cls._get_redis()
            r.publish(channel, message_json)
            logger.info("Published realtime update to %s: event_id=%s, reason=%s", channel, event_id, reason)
        except Exception as exc:
            logger.warning("Failed to publish realtime update to %s: %s", channel, exc)

