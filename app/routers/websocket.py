from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid

from app.core.connection import manager


router = APIRouter()


@router.websocket("/ws/{chat_type}")
async def websocket_endpoint(websocket: WebSocket, chat_type: str):
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)

    try:
        data = await websocket.receive_json()
        interests = data.get("interests", [])

        partner_id = await manager.find_match(connection_id, chat_type, interests)

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

        while True:
            data = await websocket.receive_json()

            if data["type"] == "message":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "message", "message": data["message"]},
                        partner_id,
                    )

            elif data["type"] == "typing":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "typing", "isTyping": data["isTyping"]},
                        partner_id,
                    )

            elif data["type"] == "video-signal":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "video-signal", "signal": data["signal"]},
                        partner_id,
                    )

            elif data["type"] == "find-new":
                if connection_id in manager.matches:
                    old_partner_id = manager.matches[connection_id]
                    if old_partner_id in manager.matches:
                        del manager.matches[old_partner_id]
                    del manager.matches[connection_id]

                    await manager.send_personal_message(
                        {"type": "system", "message": "Your chat partner has disconnected."},
                        old_partner_id,
                    )

                interests = data.get("interests", [])
                new_partner_id = await manager.find_match(connection_id, chat_type, interests)

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
                else:
                    await manager.send_personal_message(
                        {"type": "system", "message": "Waiting for someone to connect..."},
                        connection_id,
                    )

    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception:
        manager.disconnect(connection_id)
