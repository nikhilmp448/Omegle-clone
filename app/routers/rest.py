from fastapi import APIRouter
import uuid

from app.core.connection import manager
from app.models import *


router = APIRouter(prefix="/api")


@router.get("/health")
async def api_health():
    return {"status": "ok"}


@router.get("/online")
async def api_online():
    return {"online": len(manager.active_connections) + len(manager.rest_sessions)}


@router.post("/session/start")
async def api_start_session(req: StartSessionRequest):
    connection_id = str(uuid.uuid4())
    manager.rest_sessions.add(connection_id)
    partner_id = await manager.find_match(connection_id, req.chat_type, req.interests or [])
    if partner_id:
        await manager.send_personal_message(
            {"type": "system", "message": "You've been connected to a stranger!"},
            connection_id,
        )
        await manager.send_personal_message(
            {"type": "system", "message": "You've been connected to a stranger!"},
            partner_id,
        )
        await manager.send_personal_message({"type": "webrtc-init"}, connection_id)
    else:
        await manager.send_personal_message(
            {"type": "system", "message": "Waiting for someone to connect..."},
            connection_id,
        )
    await manager.broadcast_online_count()
    return {"connection_id": connection_id, "matched": bool(partner_id), "partner_id": partner_id}


@router.delete("/session/{connection_id}")
async def api_end_session(connection_id: str):
    manager.disconnect(connection_id)
    return {"ok": True}


@router.get("/status/{connection_id}")
async def api_status(connection_id: str):
    partner_id = manager.matches.get(connection_id)
    return {"connection_id": connection_id, "partner_id": partner_id}


@router.get("/updates/{connection_id}")
async def api_updates(connection_id: str):
    messages = manager.rest_inbox.get(connection_id, [])
    manager.rest_inbox[connection_id] = []
    return {"messages": messages}


@router.post("/message")
async def api_message(req: MessageRequest):
    connection_id = req.connection_id
    if connection_id in manager.matches:
        partner_id = manager.matches[connection_id]
        await manager.send_personal_message(
            {"type": "message", "message": req.message},
            partner_id,
        )
        return {"sent": True}
    return {"sent": False}


@router.post("/typing")
async def api_typing(req: TypingRequest):
    connection_id = req.connection_id
    if connection_id in manager.matches:
        partner_id = manager.matches[connection_id]
        await manager.send_personal_message(
            {"type": "typing", "isTyping": req.isTyping},
            partner_id,
        )
        return {"sent": True}
    return {"sent": False}


@router.post("/video-signal")
async def api_video_signal(req: VideoSignalRequest):
    connection_id = req.connection_id
    if connection_id in manager.matches:
        partner_id = manager.matches[connection_id]
        await manager.send_personal_message(
            {"type": "video-signal", "signal": req.signal},
            partner_id,
        )
        return {"sent": True}
    return {"sent": False}


@router.post("/find-new")
async def api_find_new(req: FindNewRequest):
    connection_id = req.connection_id
    if connection_id in manager.matches:
        old_partner_id = manager.matches[connection_id]
        if old_partner_id in manager.matches:
            del manager.matches[old_partner_id]
        if connection_id in manager.matches:
            del manager.matches[connection_id]
        await manager.send_personal_message(
            {"type": "system", "message": "Your chat partner has disconnected."},
            old_partner_id,
        )
    new_partner_id = await manager.find_match(connection_id, "text", req.interests or [])
    if new_partner_id:
        await manager.send_personal_message(
            {"type": "system", "message": "You've been connected to a new stranger!"},
            connection_id,
        )
        await manager.send_personal_message(
            {"type": "system", "message": "You've been connected to a stranger!"},
            new_partner_id,
        )
        await manager.send_personal_message({"type": "webrtc-init"}, connection_id)
        return {"matched": True, "partner_id": new_partner_id}
    else:
        await manager.send_personal_message(
            {"type": "system", "message": "Waiting for someone to connect..."},
            connection_id,
        )
        return {"matched": False}
