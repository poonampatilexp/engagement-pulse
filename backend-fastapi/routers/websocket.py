import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from database import SessionLocal
import models
from permissions import can_access_organisation
from websocket_manager import connection_manager
from ws_ticket_service import WebSocketTicketService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def handle_organisation_websocket(
    websocket: WebSocket,
    organisation_id: int,
) -> None:
    """Handles real-time organisation WebSocket connections.

    Security & Access Control:
    1. Authenticates using a short-lived single-use connection ticket (?ticket=...).
       - Missing, invalid, or expired ticket -> closes with code 4401 (Unauthorized).
    2. Enforces multi-tenant isolation:
       - User must have access to organisation_id -> closes with code 4403 (Forbidden).
    3. Guarantees single-use semantics by atomically consuming the ticket in Redis.
    4. Subscribes client to cross-instance Redis Pub/Sub events for the organisation.
    """
    ticket = websocket.query_params.get("ticket")
    if not ticket:
        logger.warning("Rejected WebSocket connection: missing ticket for org %d", organisation_id)
        await websocket.close(code=4401)
        return

    # Single-use atomic consumption via Redis GETDEL
    user_id = WebSocketTicketService.consume_ticket(ticket)
    if not user_id:
        logger.warning("Rejected WebSocket connection: invalid or expired ticket for org %d", organisation_id)
        await websocket.close(code=4401)
        return

    # Verify user existence and active status
    with SessionLocal() as db:
        user = db.execute(
            select(models.User).where(models.User.id == user_id, models.User.is_active == True)
        ).scalar_one_or_none()

        if not user:
            logger.warning("Rejected WebSocket connection: user %d not found or inactive", user_id)
            await websocket.close(code=4401)
            return

        # Enforce multi-tenant access
        if not can_access_organisation(user, organisation_id, db=db):
            logger.warning("Rejected WebSocket connection: user %d forbidden from org %d", user_id, organisation_id)
            await websocket.close(code=4403)
            return

    # Handshake accepted
    await websocket.accept()
    await connection_manager.connect(organisation_id, websocket)

    try:
        while True:
            # Keep connection open; receive any keepalive frames or pings from frontend
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally from org %d", organisation_id)
    except Exception as exc:
        logger.warning("WebSocket error for org %d: %s", organisation_id, exc)
    finally:
        await connection_manager.disconnect(organisation_id, websocket)


@router.websocket("/ws/organisations/{organisation_id}/updates")
@router.websocket("/ws/organisations/{organisation_id}/updates/")
@router.websocket("/ws/organisations/{organisation_id}")
@router.websocket("/ws/organisations/{organisation_id}/")
async def websocket_organisation_updates(
    websocket: WebSocket,
    organisation_id: int,
):
    await handle_organisation_websocket(websocket, organisation_id)

