from typing import Dict, List, Set
import random
import asyncio
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.waiting_text: Dict[str, Set[str]] = {}
        self.waiting_video: Dict[str, Set[str]] = {}
        self.matches: Dict[str, str] = {}
        self.rest_sessions: Set[str] = set()
        self.rest_inbox: Dict[str, List[dict]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        await self.broadcast_online_count()
        return connection_id

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.rest_sessions:
            self.rest_sessions.discard(connection_id)
        if connection_id in self.rest_inbox:
            del self.rest_inbox[connection_id]

        for interest, connections in self.waiting_text.items():
            if connection_id in connections:
                connections.remove(connection_id)

        for interest, connections in self.waiting_video.items():
            if connection_id in connections:
                connections.remove(connection_id)

        if connection_id in self.matches:
            partner_id = self.matches[connection_id]
            if partner_id in self.active_connections:
                asyncio.create_task(self.send_personal_message(
                    {"type": "system", "message": "Your chat partner has disconnected."},
                    partner_id
                ))
            if connection_id in self.matches:
                del self.matches[connection_id]
            if partner_id in self.matches:
                del self.matches[partner_id]

        asyncio.create_task(self.broadcast_online_count())

    async def find_match(self, connection_id: str, chat_type: str, interests: List[str]):
        if not interests:
            interests = ["general"]

        waiting_dict = self.waiting_text if chat_type == "text" else self.waiting_video

        for interest in interests:
            if interest in waiting_dict and waiting_dict[interest]:
                match_candidates = list(waiting_dict[interest])
                if match_candidates:
                    partner_id = random.choice(match_candidates)
                    waiting_dict[interest].remove(partner_id)
                    self.matches[connection_id] = partner_id
                    self.matches[partner_id] = connection_id
                    return partner_id

        for interest in interests:
            if interest not in waiting_dict:
                waiting_dict[interest] = set()
            waiting_dict[interest].add(connection_id)

        return None

    async def send_personal_message(self, message, connection_id: str):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(message)
        elif connection_id in self.rest_sessions:
            if connection_id not in self.rest_inbox:
                self.rest_inbox[connection_id] = []
            self.rest_inbox[connection_id].append(message)

    async def broadcast_online_count(self):
        online = len(self.active_connections) + len(self.rest_sessions)
        for conn_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_json({"type": "online", "count": online})
            except Exception:
                pass


manager = ConnectionManager()
