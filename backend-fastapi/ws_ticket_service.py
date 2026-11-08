import logging
import secrets
from typing import Optional
import redis
from config import settings

logger = logging.getLogger(__name__)


class WebSocketTicketService:
    TICKET_TTL = 30  # seconds

    @classmethod
    def _get_redis(cls) -> redis.Redis:
        return redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    @classmethod
    def create_ticket(cls, user_id: int) -> str:
        """Generates a cryptographically random, single-use ticket for WebSocket

        authentication.

        Stored in Redis with a short 30-second TTL.
        """
        ticket = secrets.token_urlsafe(32)
        try:
            r = cls._get_redis()
            r.set(f"ws_ticket:{ticket}", str(user_id), ex=cls.TICKET_TTL)
            logger.info("Created WebSocket ticket for user %d (TTL=%ds)", user_id, cls.TICKET_TTL)
        except Exception as exc:
            logger.error("Failed to store WebSocket ticket in Redis: %s", exc)
            raise
        return ticket

    @classmethod
    def consume_ticket(cls, ticket: str) -> Optional[int]:
        """Atomically retrieves and deletes the ticket from Redis using GETDEL.

        Returns the user ID if the ticket is valid, otherwise None. Guarantees
        single-use semantics.
        """
        if not ticket or not isinstance(ticket, str):
            return None

        key = f"ws_ticket:{ticket}"
        try:
            r = cls._get_redis()
            user_id_bytes = r.getdel(key)
            if user_id_bytes:
                user_id = int(user_id_bytes.decode("utf-8"))
                logger.info("Successfully consumed WebSocket ticket for user %d", user_id)
                return user_id
        except Exception as exc:
            logger.warning("Error consuming WebSocket ticket '%s': %s", key, exc)
            return None
        return None

