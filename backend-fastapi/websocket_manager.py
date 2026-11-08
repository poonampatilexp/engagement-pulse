import asyncio
import json
import logging
from typing import Optional
from fastapi import WebSocket
import redis.asyncio as aioredis
from config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active local WebSocket connections and bridges cross-instance

    events via Redis Pub/Sub using redis.asyncio.
    """

    def __init__(self):
        # organisation_id -> set[WebSocket]
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._running: bool = False

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, organisation_id: int, websocket: WebSocket) -> None:
        """Register a newly connected WebSocket for an organisation."""
        if not self._listener_task or self._listener_task.done():
            await self.start_redis_listener()

        async with self._get_lock():
            if organisation_id not in self._connections:
                self._connections[organisation_id] = set()
            self._connections[organisation_id].add(websocket)
            total = len(self._connections[organisation_id])
            logger.info("WebSocket connected for organisation %d (active on this instance: %d)", organisation_id, total)

    async def disconnect(self, organisation_id: int, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket."""
        async with self._get_lock():
            if organisation_id in self._connections:
                self._connections[organisation_id].discard(websocket)
                if not self._connections[organisation_id]:
                    del self._connections[organisation_id]
                logger.info("WebSocket disconnected for organisation %d", organisation_id)

    async def broadcast_to_local(self, organisation_id: int, message: str) -> None:
        """Send message text to all WebSockets connected to this instance for

        the organisation.
        """
        async with self._get_lock():
            sockets = list(self._connections.get(organisation_id, []))

        if not sockets:
            return

        dead_sockets: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception as exc:
                logger.warning("Failed to send WebSocket message to client in org %d: %s", organisation_id, exc)
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._get_lock():
                for ws in dead_sockets:
                    if organisation_id in self._connections:
                        self._connections[organisation_id].discard(ws)
                        if not self._connections[organisation_id]:
                            del self._connections[organisation_id]

    async def start_redis_listener(self) -> None:
        """Start the background task listening to Redis Pub/Sub."""
        if self._listener_task and not self._listener_task.done():
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._redis_pubsub_loop())
        logger.info("Started Redis Pub/Sub listener task via redis.asyncio")

    async def stop_redis_listener(self) -> None:
        """Stop the background Redis Pub/Sub listener task."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        logger.info("Stopped Redis Pub/Sub listener task")

    async def _redis_pubsub_loop(self) -> None:
        """Background coroutine that subscribes to Redis Pub/Sub pattern

        'fastapi:org:*' using redis.asyncio. When a message is published by any
        FastAPI instance or Dramatiq worker, it routes it to local WebSockets.
        """
        pattern = "fastapi:org:*"
        while self._running:
            client = None
            pubsub = None
            try:
                client = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                pubsub = client.pubsub()
                await pubsub.psubscribe(pattern)
                logger.info("Subscribed to Redis Pub/Sub pattern '%s' for live updates", pattern)

                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message and message.get("type") == "pmessage":
                        channel = message.get("channel", "")  # e.g. "fastapi:org:1"
                        data = message.get("data")
                        try:
                            org_id = int(channel.split(":")[-1])
                            if data:
                                await self.broadcast_to_local(org_id, data)
                        except (ValueError, TypeError) as parse_err:
                            logger.error("Failed to parse org_id from channel '%s': %s", channel, parse_err)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._running:
                    logger.warning("Redis Pub/Sub connection error (%s). Reconnecting in 2s...", exc)
                    await asyncio.sleep(2)
            finally:
                if pubsub:
                    try:
                        await pubsub.punsubscribe(pattern)
                        await pubsub.close()
                    except Exception:
                        pass
                if client:
                    try:
                        await client.close()
                    except Exception:
                        pass


connection_manager = ConnectionManager()

